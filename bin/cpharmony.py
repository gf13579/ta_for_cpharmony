# cpharmony.py

import json
import os
import sys
from loguru import logger
from pprint import pformat

# sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import Scheme, Argument, Event, Script
import splunklib.results as results
from cpharmonylib import cpharmony_connector

# sys.path.append(
#     os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", "SA-VSCode", "bin")
# import splunk_debug as dbg
# dbg.enable_debugging(timeout=25)


log_file = os.environ["SPLUNK_HOME"] + "/var/log/splunk/ta_for_cpharmony.log"
logger.remove()
logger.add(sink=log_file, level="INFO")
logger.add(sink=sys.stderr, level="ERROR")

# for development
logger.add(sink=log_file, level="DEBUG")


class MyScript(Script):
    """All modular inputs should inherit from the abstract base class Script
    from splunklib.modularinput.script.
    They must override the get_scheme and stream_events functions, and,
    if the scheme returned by get_scheme has Scheme.use_external_validation
    set to True, the validate_input function.
    """

    def get_scheme(self):
        # "CPHarmony" is the name Splunk will display to users for this input.
        scheme = Scheme("CPHarmony")

        scheme.description = "Streams events containing dork search results."
        scheme.use_external_validation = False

        # Set to false so each input can have an optional interval parameter
        scheme.use_single_instance = False

        hoursago_argument = Argument("query_hours_ago")
        hoursago_argument.title = "Query Age (hours ago)"
        hoursago_argument.data_type = Argument.data_type_string
        hoursago_argument.description = "Controls variables.queryParam.dateRange.from"
        scheme.add_argument(hoursago_argument)

        username_argument = Argument("username")
        username_argument.title = "Username"
        username_argument.data_type = Argument.data_type_string
        username_argument.description = (
            "Username for connection - setup password within TA's setup page"
        )
        scheme.add_argument(username_argument)

        return scheme

    def validate_input(self, validation_definition):
        """In this example we are using external validation to verify that min is
        less than max. If validate_input does not raise an Exception, the input is
        assumed to be valid. Otherwise it prints the exception as an error message
        when telling splunkd that the configuration is invalid.

        When using external validation, after splunkd calls the modular input with
        --scheme to get a scheme, it calls it again with --validate-arguments for
        each instance of the modular input in its configuration files, feeding XML
        on stdin to the modular input to do validation. It is called the same way
        whenever a modular input's configuration is edited.

        :param validation_definition: a ValidationDefinition object
        """
        # Get the parameters from the ValidationDefinition object,

        hours_ago = str(validation_definition.parameters["hours_ago"])
        if not hours_ago or (hours_ago == ""):
            hours_ago = "1"

        logger.debug(f"Chance to validate hours_ago: {hours_ago}")

        if not hours_ago.isnumeric():
            raise ValueError("hours_ago must be an integer")

    def stream_events(self, inputs, ew):
        """This function handles all the action: splunk calls this modular input
        without arguments, streams XML describing the inputs to stdin, and waits
        for XML on stdout describing events.

        If you set use_single_instance to True on the scheme in get_scheme, it
        will pass all the instances of this input to a single instance of this
        script.

        :param inputs: an InputDefinition object
        :param ew: an EventWriter object
        """

        # there should only be one input as we're setting scheme.use_single_instance = False
        stanza = list(inputs.inputs.keys())[0]
        logger.debug(f"stanza name is {stanza}")

        # Get mod input params
        hours_ago = str(inputs.inputs[stanza]["query_hours_ago"])
        username = str(inputs.inputs[stanza].get("username"))

        password = None
        storage_passwords = self.service.storage_passwords
        for k in storage_passwords:
            p = str(k.content.get("clear_password"))
            realm = str(k.content.get("realm"))
            if realm == "ta_for_cpharmony_realm":
                password = p
                break

        logger.debug("instantiating connector")
        cp_connector = cpharmony_connector(
            username=username, password=password, region="ap", verify=False
        )

        if not cp_connector.login():
            logger.error("Failed to login")
            return

        logger.debug("Starting queries")

        results = cp_connector.query_active_attacks(hours_ago=hours_ago)

        for r in results:
            logger.debug(f"type(r) is {type(r)}")
            if isinstance(r, list):
                for list_item in r:
                    event = Event()
                    event.stanza = stanza
                    event.data = json.dumps(list_item)
                    ew.write_event(event)
            else:
                event = Event()
                event.stanza = stanza
                event.data = json.dumps(r)
                # log OpTimeUTC for diagnosing timestamp issues
                if "Base" in r:
                    if "OpTimeUTC" in r["Base"]:
                        optime_utc = r["Base"]["OpTimeUTC"]
                        logger.info(
                            f"Writing event with ['Base']['OpTimeUTC'] set to {optime_utc}"
                        )
                    else:
                        logger.info("Writing event with no OpTimeUTC value in ['Base']")
                else:
                    logger.info("Writing event with no ['Base']")

                # Use event time - Base.OpTimeUTC - if present
                # logger.debug("Checking whether Base is in r")
                # if "Base" in r:
                #     if "OpTimeUTC" in r["Base"]:
                #         logger.debug("Checking whether OpTimeUTC is in r Base")
                #         event.time = int(round(int(r["Base"]["OpTimeUTC"]) / 1000, 0))
                #         logger.debug(f"event.time is {event.time}")
                ew.write_event(event)

        logger.debug(f"Finished queries. Events created: {len(results)}")

    def get_rows_from_lookup(self, spl_query):
        rr = results.ResultsReader(self.service.jobs.oneshot(spl_query))

        result_list = []
        for result in rr:
            if isinstance(result, results.Message):
                # Diagnostic messages returned in the results
                logger.info("%s: %s" % (result.type, result.message))
            elif isinstance(result, dict):
                # cast to dict as we don't need an ordered dict
                result_list.append(dict(result))
        assert rr.is_preview is False

        return result_list


if __name__ == "__main__":
    sys.exit(MyScript().run(sys.argv))
