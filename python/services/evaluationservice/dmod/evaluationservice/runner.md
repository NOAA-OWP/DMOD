# The Evaluation Service Runner

### Purpose

The Evaluation Service Runner (found in `runner.py`), refered to simply as 'the runner', is a process that runs outside
of the context of the evaluation service.

It is responsible for listening for requests to launch evaluations and acting upon them.

### Important Concepts

The runner listens to a redis stream for messages pertaining to it and pulls pertinent information when deemed important.

A Redis Stream is just a simple message queue. Each message within the queue is just a set of key value pairs. Calling
`xadd` allows you or a program to add a new set of key value pairs and an id may be associated with it. If an id is not given,
the id will correspond with the numeric datetime of when the message was stored. The commands `xread` and `xreadgroup`
may be used to read new messages from a given message id. Starting at `"0"` allows you to read from the earliest
message onwards, `">"` allows you to only read new messages (ignoring all previous messages), and offering an id will
let you read every message that comes _after_ that id. `xread` will give you a message and `xreadgroup` will take
the message and reserve it for a single consumer within a consumer group. Only one consumer may hold a message
within a group at any given time. Multiple groups may read and claim messages at the same time. `xclaim` allows one
consumer in a group to claim ownership of a message from another consumer within the group and `xack` tells the group
that it is done processing the message, releases ownership, and the group will not read the message again. This
allows for workstealing and prevents the overprocessing of a single message. `xdel` deletes the message from the
queue altogether. Calling `xdel` is a good way of keeping _any_ further processing of a message and is a good thing
to do when operating a work queue. Once requirements for work have been fulfilled, the record may be removed to
ensure that it is not attempted again.

Sets of actions generally correlate to groups. If something is responsible for controlling a light switch, a group
may be responsible for the incoming messages. Consumers within these groups generally correlate to actors that may
perform the actions granted to the group. If there are 4 consumers within a single group, Consumer C might be able
to claim ownership of message X within the group and consumers A, B, and D will not. If message Y comes through,
consumers A, B, or D may be able to claim that message for themselves and perform work while consumer C consumes
message X. This helps coordinate work across computational nodes. If consumers A, B, C, and D all work on different
nodes, one consumer may claim work and consume its own resources without disrupting the others. If more work
needs to be done simultaneously, more consumers may be added for horizontal scaling.

Messages are caught in the main thread, evaluations are run in child processes, and there is a second thread that
monitors running processes to determine when shared scope should be destroyed and when messages should be removed
from the stream. The `concurrent.futures` interface is used to track running evaluations, so the monitoring thread
is able to poll the evaluations its track to see if processing within the child process has concluded.

#### How does this differ from PubSub?

The runner was originally implemented by subscribing to a Redis PubSub channel. A PubSub channel is a single stream
that clients may publish data to and other clients may subscribe to. Subscribers may 'listen' to the channel and
each subscriber will get the message in real time. If a subscriber misses a message, they will miss it and cannot
read it later. Imagine a PubSub channel is a TV channel. One or more entities may broadcast video through it and the
audience may do with what they receive as they like. The audience does not quite have the ability to respond to the
broadcaster unless they themselves become a broadcaster and the original broadcasters become audience members.

PubSub works great for real time dissemination of data, but if used to coordinate work, like the runner previously,
_all_ subscribers will attempt to perform the same work. If there are four runners on four machines, each will
attempt to run the same evaluation on their own machine because they have no way of knowing that the others are
performing the same work.

#### The Worker

The worker, found in `worker.py`, is the entity that _actually_ calls `dmod.evaluations` in order to perform
evaluation duties, _not the runner._ The runner will collect information from messages and call the runner in a
child process with the received parameters.

The worker may be called via the command line to perform evaluations manually. If there is a need to script out
evaluations directly to `dmod.evaluations` and bypass the service entirely, the worker contains an excellent example
of how to do so.

#### How does the runner listen?

`runner:listen` is called from `runner:main` with instructions on how to connect to redis and the limit of how many
jobs may be run at the same time.

`runner:listen`, called the listener from now on, will create a multiprocessed event to use a signal to stop
listening and spawn a thread to poll a queue of actively running `Future`s that are evaluating data. Then listener
creates a consumer for the group performing listening duties, but create the group if it is not already present.
A counter used to track errors will be created. This tracker will identify faults and count the times that they occur.
Errors are identified by where in the code base that they are thrown. If the same error from the same locations are
encountered too many times in a short period the listener will exit since this indicates a core problem of the
application. The listener continues to listen for the same reason web servers continue to function after encountering a
500+ error. A portion causes an error but it isn't clear if it should throughly halt all operations or not. It make be
due to a user request (such as a bad configuration) or it may be a freak accident that is never encountered again.

A while loop is then entered that will run until the stop signal is set. Within the loop, a generator is created that
will set itself up to read and deserialize messages it manages to grab from the redis stream. Other runners that may
be running in tandem may be able to claim messages first and prevent an instance of the runner from claiming its own
until another message is added to the stream. This is intended behavior. It allows multiple runners to run at once
on multiple machines without interfering with one another.

Each message read via the generator, which will block until a message is received, is fed into a function to interpret
the collected message. As of writing (August 30th, 2024), there are three things that may be interpreted from the
messages:

1. Launch an evaluation
2. Stop Listening
3. Ignore the message

##### Launch an Evaluation

If a message comes through stating that an evaluation should be run, the given parameters are stored in a `JobRecord`
with information on where the message came from, what generated it, what the evaluation is, and a reference to the
process running the evaluation. That is passed back to the main loop where it is stored in a queue the the monitoring
thread will poll.

##### Stop Listening

If a message comes through stating that the purpose of the message is to close, kill, or terminate the application,
the stop signal is set and nothing is returned from the interpretation function. Since the stop signal is set,
the loop will then end. The message will be acknowledged via `xack` so that the group won't read it again.

##### Ignore the Message

If a message comes through that the listener doesn't know what to do with, it is logged, and the message is
acknowledged via `xack`. Maybe there is another group that reads from the same stream that may interact with said
message or maybe there's a consumer attached to a process in the same group that may handle it. The configuration
that will cause such messages to pass through are not ideal, but they will not interupt the performance of _this_
operation.
