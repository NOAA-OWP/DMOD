# DMOD Evaluation Service

The Distributed-Model-on-Demand Evaluation Service handles requests
telling it to invoke functions from the `dmod.evaluations` module in
order to evaluate existing model data.

There are four primary components.

The first component is the worker, found at `worker.py`. This script may be called from the terminal, from another
process, or as a direct module. This component is responsible for actually carrying out evaluations. Given a
configuration defined in `dmod.evaluations`, it will call all necessary functions needed to call the code in
`dmod.evaluations` and save the output as desired.

Next is the service itself. As of 2022-07-25, it has 8 primary views:

1. The evaluation list, which shows all recent evaluations that may be examined. This is a page you can see in your browser.
2. The evaluation builder, which is a page that allows a user submit a `dmod.evaluations` configuration for evaluation.
   This is a testing view - the api and *not* the builder page should be use for running evaluations. This is a page
   you can view in your browser
3. Get Output - navigating to the output page will combine any generated evaluation output and send it to the client
   for download. This is **not** a standard web page and instead performs server side operations.
4. Launch - **the launch view is the primary service used to launch evaluations.** The builder page calls this page as
   well. Upon invocation, this view will return JSON detailing the name of the channel/evaluation that was generated,
   the key for the channel in redis that may be listened to, and the websocket address that may be attached to
   listen for results in real time. Calling this from a browser will redirect to a view that will show messages as
   they come in.
5. Listen - the listen page is an actual page that may be navigate to that will render messages from the given channel \
   in real time. Despite being provided for evaluation output, it may be used to show *any* channels' messages in \
   real-time as long as they come in through service's redis instance

Next is the runner, found in `runner.py`. This listens to the service and will launch evaluation processes.
The runner requires specialized closing procedures. See below for more details.

Lastly, there is the redis server. While it is used primarily for communication, it may be probed for diagnostic
information, such as the status of an evaluation and logged messages.

## How to Run

### Without a deployment

When running the evaluation service on a personal environment, such as a laptop, the only things that are needed are
for the libraries to be installed, redis running, the redis queue worker running, and the django server running.
The redis default host is `localhost`, the default port is `6379`, and there is no default password.
Examples down below pass arguments to redis commands to ensure that all of those values are present and connected
to the right object. If the default values are to be used, there is no need to add `--port 6379` to `redis-server`
or to add either `-h localhost`, `-p 6379`, or `-a` to `redis-cli`.

This just requires:

```shell
# If the redis server is not already running and needs to be local, you can run it in the background by calling:
redis-server --port <port> --daemonize yes

# If the redis server needs to run elsewhere, it must be started there

# Start the runner; this will create a process that will listen out for messages indefinitely. print statements from
# the runner will be printed to stdout
python runner.py &

# Launch the django server, accessible at http://127.0.0.1:9781 on the machine the command is run on
python manage.py runserver 127.0.0.1:9781
```

This will launch the redis server, the redis queue worker, and the django server in the background, with the server
being accessible at http://127.0.0.1:9781.

Alternatively, each may be run in separate terminals, which is the easiest way to go for monitoring and debugging.
That may be done by entering:

**Terminal 1:**
```shell
redis-server --port <port>
```

**Terminal 2:**
```shell
python runner.py
```

**Terminal 3:**
```shell
python manage.py runserver 127.0.0.1:9781
```

Separating the three commands into three terminals lets you see each application's stdout in real time.

It may also help to have yet another terminal open and connected to the redis instance. This may be launched by
entering:

**Terminal 4:**
```shell
redis-cli -h <host> -p <port> -a <password>
```

**IMPORTANT:** see the 'Terminating the Runner' section for rules and instructions on how to stop the runner script.


### With a deployment

Deploying the server is similar but requires a few more things. First, the environment variable `REDIS_HOST` will
need to be set. DMOD generally has a redis container named `myredis` at the address `redis` on the docker stack,
so setting `REDIS_HOST=redis` *should* do the trick. If that's used, however, the correct credentials will also need
to be included. By default, the system will attempt to get credentials via a docker secrets file dictated by the
environment variable `REDIS_PASSWORD_FILE`, which is `/run/secrets/myredis_pass` by default. If that file is not
present, it will fall back to the string dictated by the environment variable `REDIS_PASS`. If nothing is present,
it will attempt an empty password, which is the default for redis.

Once deployed, ensure that the following commands are run:

```shell
python runner.py &
```

```shell
python manage.py runserver 127.0.0.1:9781
```

As long as the server's user facing ports are accessible and redis is correctly configured, it should be smooth sailing.

## Terminating the Runner

`runner.py` blocks itself by listening out for messages. As a result, it can't handle signal interrupts, like typing
`ctrl+c` from the command line. To close or terminate the runner, there are several options. The preferred method is by
using `kill_runner.py`, which will contact the same instance that the `runner` uses and close all active runners.
Similarly, the following can be called from the command line to close the runner:

```shell
redis-cli -h <instance host> -p <instance port> -a <instance password> publish <channel name> '{"purpose": "close"}'
```

As above, the values of `-h`, `-p`, and `-a` are only necessary if they are not the default
(`localhost`, `6379`, and none, respectively). This will send a message and close all runners listening to that
channel for instruction.

Lastly, the commands `kill <pid>` and `kill -2 <pid>` may be used from the terminal to kill the application.

**Never kill the runner by calling `kill -9 <pid>`**. This will indeed stop the runner, but it will leak resources in
the process.

## Environment Variables

There are a score of environment variables that may be utilized, though their configuration is not require.
Configuration is only needed if slightly different behavior is desired, such as redis credentials and queue names.


<table>
   <!-- this is in an html table rather than a markdown table in order to keep it readable - otherwise lines can extend over 300 characters -->
    <caption>Environment Variables as of 2022-07-05</caption>
    <thead>
        <th>Variable</th>
        <th>Purpose</th>
        <th>Example</th>
        <th>Required</th>
        <th>Default Value</th>
    </thead>
    <tbody>
        <tr>
            <td><code>EVALUATION_VERBOSITY</code></td>
            <td>
                Controls how much data should be sent through the internal broadcasting mechanism.
                `QUIET` sends **no** data through the channel, `ALL` will send all raw data through the channel.
                Case-insensitive.
            </td>
            <td>
                <ul>
                    <li><code>QUIET</code> - No data is sent through channels and data is only written to disk</li>
                    <li><code>NORMAL</code> - Only basic information will be communicated through redis channels</li>
                    <li><code>LOUD</code> - Detailed diagnostic information will be passed through channels</li>
                    <li><code>ALL</code> - <b>all</b> generated data will be published through the channel</li>
                </ul>
            </td>
            <td>
                ❌
            </td>
            <td>
                <code>NORMAL</code>
            </td>
        </tr>
        <tr>
            <td><code>EVALUATION_START_DELAY</code></td>
            <td>
                The number of seconds to delay an evaluation. Helps give a little bit of time for a monitor to attach
                prior to processing
            </td>
            <td>
                <code>8</code>
            </td>
            <td>
                ❌
            </td>
            <td>
                <code>5</code>
            </td>
        </tr>
        <tr>
            <td><code>DEBUG</code></td>
            <td>
                Whether the service is set to run in debug mode or not. Case-insensitive.
            </td>
            <td>
                 <code>yes</code>, <code>TrUe</code>, <code>ON</code>, <code>nO</code>, <code>false</code>
            </td>
            <td>
                ❌
            </td>
            <td>
                <code>False</code>
            </td>
        </tr>
        <tr>
            <td><code>REDIS_PASSWORD_FILE</code></td>
            <td>
                The path to a file containing the password to the targetted redis instance
                (intended, but not required to be a docker secret)
            </td>
            <td>
                <code>/run/secrets/redis_pword</code>
            </td>
            <td>
                ❌
            </td>
            <td>
                <code>/run/secrets/myredis_pass</code>
            </td>
        </tr>
        <tr>
            <td><code>REDIS_PASS</code></td>
            <td>
                The plaintext password to a redis instance
            </td>
            <td>
                <code>mYpAsSwOrd</code>
            </td>
            <td>
                ❌
            </td>
            <td>
            </td>
        </tr>
        <tr>
            <td><code>APPLICATION_NAME</code></td>
            <td>
                A name that may be referenced to describe the service
            </td>
            <td>
                <code>"Service used for evaluations"</code>
            </td>
            <td>
                ❌
            </td>
            <td>
                <code>"Evaluation Service"</code>
            </td>
        </tr>
        <tr>
            <td><code>EVALUATION_QUEUE_NAME</code></td>
            <td>
                The name of the queue to stick evaluation requests into
            </td>
            <td>
                <code>job_queue</code>
            </td>
            <td>
                ❌
            </td>
            <td>
                <code>evaluation_jobs</code>
            </td>
        </tr>
        <tr>
            <td><code>REDIS_HOST</code></td>
            <td>
                The address of the redis instance to connect to. In a docker environment, this should be set to either
                a dedicated redis address or the name of the desired redis container on the common docker network.
                Unless that container has been onfigured to have a different name on the network, it <b>should</b> just
                be the name of the container, such as <code>myredis</code>
            </td>
            <td>
                <code>192.168.1.35</code>
            </td>
            <td>
                ❌
            </td>
            <td>
                <code>localhost</code>
            </td>
        </tr>
        <tr>
            <td><code>REDIS_PORT</code></td>
            <td>
                The port at which the desired redis instance communicates through. This <b>must</b> be an integer value
            </td>
            <td>
                <code>63279</code>
            </td>
            <td>
                ❌
            </td>
            <td>
                <code>6379</code>
            </td>
        </tr>
        <tr>
            <td><code>RQ_HOST</code></td>
            <td>
                The address of the redis instance that manages worker executions. This is only needed if a
                redis instance other than the base instance needs to be used.
            </td>
            <td>
                <code>192.168.1.35</code>
            </td>
            <td>
                ❌
            </td>
            <td>
            </td>
        </tr>
        <tr>
            <td><code>RQ_PORT</code></td>
            <td>
                The port of the redis instance that manages worker executions. This is only needed if a
                redis instance other than the base instance needs to be used.
            </td>
            <td>
                <code>8675</code>
            </td>
            <td>
                ❌
            </td>
            <td>
            </td>
        </tr>
        <tr>
            <td><code>RQ_PASSWORD</code></td>
            <td>
                The password of the redis instance that manages worker executions. This is only needed if a
                redis instance other than the base instance needs to be used.
            </td>
            <td>
                <code>rqReDiSPASSwd</code>
            </td>
            <td>
                ❌
            </td>
            <td>
            </td>
        </tr>
        <tr>
            <td><code>CHANNEL_HOST</code></td>
            <td>
                The address of the redis instance that hosts needed communication channels. This is only needed if a
                redis instance other than the base instance needs to be used.
            </td>
            <td>
                <code>192.168.1.35</code>
            </td>
            <td>
                ❌
            </td>
            <td>
            </td>
        </tr>
        <tr>
            <td><code>CHANNEL_PORT</code></td>
            <td>
                The port of the redis instance that hosts needed communication channels. This is only needed if a
                redis instance other than the base instance needs to be used.
            </td>
            <td>
                <code>60375</code>
            </td>
            <td>
                ❌
            </td>
            <td>
            </td>
        </tr>
        <tr>
            <td><code>DEFAULT_LOGGER_NAME</code></td>
            <td>
                The name of the python log configuration that standard service log messages will go through
            </td>
            <td>
                <code>eval_service</code>
            </td>
            <td>
                ❌
            </td>
            <td>
               <code>APPLICATION_NAME.replace(" ", "")</code>
            </td>
        </tr>
        <tr>
            <td><code>DEFAULT_SOCKET_LOGGER_NAME</code></td>
            <td>
                The name of the python log configuration that web socket log messages will go through
            </td>
            <td>
                <code>logs_for_websockets</code>
            </td>
            <td>
                ❌
            </td>
            <td>
               <code>SocketLogger</code>
            </td>
        </tr>
        <tr>
            <td><code>EVALUATION_SERVICE_LOG_LEVEL</code></td>
            <td>
                The name of the python log level that serves as the minimum level. If <code>WARNING</code> is designated,
               only messages of level <code>WARNING</code> and up will be written (<code>WARNING</code>,
               <code>ERROR</code>, and <code>CRITICAL</code>).
            </td>
            <td>
               <ul>
                  <li><code>CRITICAL</code>/<code>FATAL</code></li>
                  <li><code>ERROR</code></li>
                  <li><code>WARN</code>/<code>WARNING</code></li>
                  <li><code>INFO</code></li>
                  <li><code>DEBUG</code></li>
                  <li><code>NOTSET</code></li>
               </ul>
            </td>
            <td>
                ❌
            </td>
            <td>
               <code>"DEBUG"</code> if the variable <code>DEBUG</code> is true, otherwise <code>"INFO"</code>
            </td>
        </tr>
        <tr>
            <td><code>EVALUATION_SERVICE_SOCKET_LOG_LEVEL</code></td>
            <td>
               The name of the python log level that serves as the minimum level for log messages for asynchronous
               socket processing. If <code>WARNING</code> is designated,
               only messages of level <code>WARNING</code> and up will be written (<code>WARNING</code>,
               <code>ERROR</code>, and <code>CRITICAL</code>).
            </td>
            <td>
               <ul>
                  <li><code>CRITICAL</code>/<code>FATAL</code></li>
                  <li><code>ERROR</code></li>
                  <li><code>WARN</code>/<code>WARNING</code></li>
                  <li><code>INFO</code></li>
                  <li><code>DEBUG</code></li>
                  <li><code>NOTSET</code></li>
               </ul>
            </td>
            <td>
                ❌
            </td>
            <td>
               <code>"DEBUG"</code> if the variable <code>DEBUG</code> is true, otherwise <code>"INFO"</code>
            </td>
        </tr>
        <tr>
            <td><code>APPLICATION_LOG_PATH</code></td>
            <td>
               The path to the primary log file.
            </td>
            <td>
               <code>path/to/file.log</code>
            </td>
            <td>
                ❌
            </td>
            <td>
               <code>${DEFAULT_LOGGER_NAME}.log</code>
            </td>
        </tr>
        <tr>
            <td><code>EVALUATION_SOCKET_LOG_PATH</code></td>
            <td>
               The path to the asynchronous web socket logs.
            </td>
            <td>
               <code>path/to/socket_file.lOg</code>
            </td>
            <td>
                ❌
            </td>
            <td>
               <code>EvaluationSockets.log</code>
            </td>
        </tr>
        <tr>
            <td><code>MAXIMUM_LOG_SIZE</code></td>
            <td>
               The maximum size that log files may be if rotating logs are used. The unit is in megabytes if none
               are indicated. The range of acceptable values are from [1KB, 1TB). Using anything a gigabyte or higher
               is not advised. Indicated sizes less than 1KB are upgraded to 1KB. Anything described as being in a
               unit other than B, KB, MB, or GB will be expressed in MB.
            </td>
            <td>
               <code>10</code>, <code>20KB</code>, <code>30gB</code>, <code>0.8GB</code>
            </td>
            <td>
                ❌
            </td>
            <td>
               <code>5</code>
            </td>
        </tr>
        <tr>
            <td><code>MAXIMUM_LOGFILE_BACKUPS</code></td>
            <td>
               The maximum number of log files to keep backed up if a rotating logger is used
            </td>
            <td>
               <code>10</code>
            </td>
            <td>
                ❌
            </td>
            <td>
               <code>5</code>
            </td>
        </tr>
        <tr>
            <td><code>DEFAULT_LOG_HANDLER</code></td>
            <td>
               The default logging handler class to use when writing logged messages. See the
               <a href="https://docs.python.org/3/library/logging.html">Python logging documentation</a> and the
               <a href="https://docs.python.org/3/library/logging.handlers.html">Python Log Handler documentation</a>
               for options.
            </td>
            <td>
               <code>logging.FileHandler</code>, <code>logging.handlers.SocketHandler</code>
            </td>
            <td>
                ❌
            </td>
            <td>
               <code>logging.handlers.RotatingFileHandler</code>
            </td>
        </tr>
        <tr>
            <td><code>DEFAULT_LOGGING_HOST</code></td>
            <td>
               The address to the host of a logging service if one is intended to be used
            </td>
            <td>
               <code>10.3.9.88</code>, <code>https://logging.example.com/logging/host</code>
            </td>
            <td>
               ❓; Only if a logger is used that requires it, such as <code>SocketHandler</code>,
               <code>DatagramHandler</code>, or <code>HttpHandler</code>
            </td>
            <td>
            </td>
        </tr>
        <tr>
            <td><code>DEFAULT_LOGGING_PORT</code></td>
            <td>
               The port on the host of a logging service if one is intended to be used
            </td>
            <td>
               <code>10.3.9.88</code>, <code>https://logging.example.com/logging/host</code>
            </td>
            <td>
               ❓; Only if a logger is used that requires it, such as <code>SocketHandler</code>,
               <code>DatagramHandler</code>, or <code>HttpHandler</code>
            </td>
            <td>
            </td>
        </tr>
        <tr>
            <td><code>LOG_FORMAT</code></td>
            <td>
               The formatting string detailing how logs should be written. Formatting options may be found in the
               [Python logging documentation](https://docs.python.org/3/library/logging.html#logrecord-attributes)
            </td>
            <td>
               <code>"%(asctime)s-%(created)f [%(levelname)s] => %(filename)s"</code>
            </td>
            <td>
                ❌
            </td>
            <td>
               <code>"[%(asctime)s] %(levelname)s: %(message)s"</code>
            </td>
        </tr>
        <tr>
            <td><code>LOG_DATEFMT</code></td>
            <td>
               The format for how time should be represented throughout the service. Formatting options may be found
               in the [Python `datetime` documentation](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes).
            </td>
            <td>
               <code>"%A, %B %d, %Y at %H:%M %p"</code>
            </td>
            <td>
                ❌
            </td>
            <td>
               <code>"%Y-%m-%d %H:%M:%S%z"</code>
            </td>
        </tr>
        <tr>
            <td><code>LOGGING_CONFIGURATION</code></td>
            <td>
               The path to a detailed configuration file for an advanced logging setup. Configuration from this
               optional file takes precedence over all else.
               See the [Python logging documentation](https://docs.python.org/3/library/logging.config.html#configuration-file-format)
               for details.
            </td>
            <td>
               <code>path/to/log_configuration.yml</code>
            </td>
            <td>
                ❌
            </td>
            <td>
            </td>
        </tr>
        <tr>
            <td><code>EVALUATION_PREFIX</code></td>
            <td>
               A prefix to use in redis instances to prevent collision with keys from other applications.
            </td>
            <td>
               <code>EVAL::UaTi--OnS</code>
            </td>
            <td>
                ❌
            </td>
            <td>
               <code>MAAS--EVALUATION</code>
            </td>
        </tr>
        <tr>
            <td><code>EVALUATION_SUNSET</code></td>
            <td>
               The time in seconds that redis entries have left to live after the system deciding that they no longer
               need to be present
            </td>
            <td>
               <code>3600</code>
            </td>
            <td>
                ❌
            </td>
            <td>
               <code>900</code>
            </td>
        </tr>
        <tr>
            <td><code>UNCHECKED_EVALUATION_LIFESPAN</code></td>
            <td>
               The time in seconds that redis entries should be present before being removed. This ensures that keys
               are removed in the case a cleanup action never occurs.
            </td>
            <td>
               <code>3600</code>
            </td>
            <td>
                ❌
            </td>
            <td>
               <code>64800</code>
            </td>
        </tr>
        <tr>
            <td><code>USE_ENVIRONMENT</code></td>
            <td>
               Whether to use dynamic environment variables. See the "Dynamic Environment Variables" section for details.
            </td>
            <td>
               <code>1</code>, <code>on</code>, <code>tRuE</code>
            </td>
            <td>
                ❌
            </td>
            <td>
               <code>False</code>
            </td>
        </tr>
        <tr>
            <td><code>REDIS_OUTPUT_KEY</code></td>
            <td>
               The key for a redis hash that contains variables describing how output should be processed.
               See the "Dynamic Environment Variables" section for details
            </td>
            <td>
               <code>MAAS::OUTPUT::KEY</code>
            </td>
            <td>
                ❌
            </td>
            <td>
            </td>
        </tr>
        <tr>
            <td><code>MAXIMUM_RUNNING_JOBS</code></td>
            <td>
               The maximum number of evaluation jobs that may run at once
            </td>
            <td>
               <code>10</code>
            </td>
            <td>
                ❌
            </td>
            <td>
               The number of available CPUs
            </td>
        </tr>
    </tbody>
</table>

## Dynamic Environment Variables

The evaluation service supports "dynamic environment" variables. This means that accessible, non-application variables
may be set for the application to use for guidance. These may be set one of two ways - as undocumented environment
variables or through a redis instance. The environment variable `USE_ENVIRONMENT` indicates that dynamic environment
variables stored within the actual environment are ok to be used. If set to a `True` value (`1`, `on`, `true`, `yes`),
any environment variable prepended by `MAAS::EVALUATION::OUTPUT::` will be read and possibly used to
configure parameters for output manipulation. These values may be things like `MAAS::EVALUATION::OUTPUT::output_writer`,
which will be read by the service writing code to determine what sort of evaluation writer to use when writing output.
Any unique parameters that that writer may need to know will also be used if included as a dynamic variable,
regardless of dynamic variable source. These values may also be accepted from a redis hash if the `REDIS_OUTPUT_KEY`
environment variable is also set to a valid hash value. All values within the indicated hash may be used as parameters.
Given the hash:
```json
   "MAAS::OUTPUT::KEY" : {
      "output_writer": "NetcdfWriter",
      "destination": "/path/to/output/destination/directory"
   }
```

The `output_writer` and `destination` variables will be available will be available for use.
These values will take precedence over standard environment variables. Given the above hash, if
`MAAS::EVALUATION::OUTPUT::output_writer=JSONWriter` is also set, `output_writer` will still be considered as
`NetcdfWriter`.  Please see `dmod.evaluations` to see options for what may be set.

## Templates

Templates are powerful building blocks belonging to the Evaluation Service that may be used to build evaluation
configurations. While each instance of the evaluation service may have its own definitions, a common set may be
found in `common_templates.sqlite`.

Running the following command will import the data into the servcie:

```bash
python3 manage.py templates import --path common_templates.sqlite
```

Configured templates may be saved and distributed by calling:

```bash
python3 manage.py templates export
```
