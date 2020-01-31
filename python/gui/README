Here is a sample web based frontend provided by Chris Tubbs.

There Requests/validation here needs to be rectified with MaaS requests/validation,
and the the Django app should be connected to the request handler end point (and/or piped directly to
the scheduler connection, as this is handling the request and validating it using the same schema validation.)

TODO align these efforts and settle on the design of request handling/validation.
One train of thought is that the request handling can be replicated as an independent service,
this falls into the "Zero Trust" type paradigm, where the web server collecting user input validates it,
and the request is then sent to the MaaS service handler and gets validated again (Depending on the deployment of
the web front end, this isn't a bad idea to mitigate MITM issues.  However, if the web server is "trusted", this is
a redunant step.  Either way, the same code can be used in both places, and should be aligned.
