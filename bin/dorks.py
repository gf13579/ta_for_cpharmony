import sys
import os
import json
from loguru import logger
import dorklib
from pprint import pprint

log_file = os.environ["SPLUNK_HOME"] + "/var/log/splunk/ta_for_dorks.log"
logger.remove()
logger.add(sink=log_file, level="INFO")
logger.add(sink=sys.stderr, level="ERROR")

# for development
logger.add(sink=log_file, level="DEBUG")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *
import splunklib.results as results


class MyScript(Script):
    """All modular inputs should inherit from the abstract base class Script
    from splunklib.modularinput.script.
    They must override the get_scheme and stream_events functions, and,
    if the scheme returned by get_scheme has Scheme.use_external_validation
    set to True, the validate_input function.
    """

    def get_scheme(self):
        # "dorks" is the name Splunk will display to users for this input.
        scheme = Scheme("Dorks")

        scheme.description = "Streams events containing dork search results."
        scheme.use_external_validation = False

        # Set to false so each input can have an optional interval parameter
        scheme.use_single_instance = False

        qdr_argument = Argument("query_date_range")
        qdr_argument.title = "Query Date Range (days)"
        qdr_argument.data_type = Argument.data_type_string
        qdr_argument.description = (
            "Filter results by discovery/index date, where supported. 0 = all time."
        )
        scheme.add_argument(qdr_argument)

        cse_id_argument = Argument("cse_id")
        cse_id_argument.title = "Google CSE ID (optional)"
        cse_id_argument.data_type = Argument.data_type_string
        cse_id_argument.description = (
            "If using Google CSE, define API key using add-on's setup page"
        )
        scheme.add_argument(cse_id_argument)

        google_get_max_wait_argument = Argument("google_get_max_wait")
        google_get_max_wait_argument.title = "Google search max delay (seconds)"
        google_get_max_wait_argument.data_type = Argument.data_type_string
        google_get_max_wait_argument.description = (
            "Wait between zero and this number of seconds when querying Google"
        )

        scheme.add_argument(google_get_max_wait_argument)

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

        query_date_range = str(validation_definition.parameters["query_date_range"])
        if not query_date_range or (query_date_range == ""):
            query_date_range = "0"

        logger.debug(f"Chance to validate query_date_range: {query_date_range}")

        if not query_date_range.isnumeric():
            raise ValueError("query_date_range must be an integer")

        google_get_max_wait = str(
            validation_definition.parameters["google_get_max_wait"]
        )
        if not google_get_max_wait.isnumeric():
            raise ValueError("google_get_max_wait must be an integer")

        """cse_id = str(validation_definition.parameters["cse_id"])
        if not cse_id or (cse_id == ""):
            cse_id = """ ""

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
        logger.debug(f"stanza is {stanza}")

        # Get mod input params
        query_date_range = str(inputs.inputs[stanza]["query_date_range"])
        cse_id = str(inputs.inputs[stanza].get("cse_id"))
        google_get_max_wait = str(inputs.inputs[stanza].get("google_get_max_wait", "5"))
        if not google_get_max_wait or (google_get_max_wait == ""):
            google_get_max_wait = 10

        google_cse_api_key = None
        storage_passwords = self.service.storage_passwords
        for k in storage_passwords:
            p = str(k.content.get("clear_password"))
            realm = str(k.content.get("realm"))
            if realm == "ta_for_dorks_realm":
                google_cse_api_key = p
                break

        dorker = dorklib.dorklib(
            cse_api_key=google_cse_api_key,
            cse_id=cse_id,
            query_date_range=query_date_range,
            google_get_max_wait=google_get_max_wait,
        )

        queries = self.get_rows_from_lookup("inputlookup dork_queries.csv")
        entities = self.get_rows_from_lookup("inputlookup dork_entities.csv")

        logger.debug(
            "Starting queries. Queries enabled: {}".format(
                len([q for q in queries if q["disabled"] not in ("1", "true", "True")])
            )
        )

        # results = dorker.do_queries(entities=entities, queries=queries)

        for r in dorker.do_queries(entities=entities, queries=queries):
            if isinstance(r, list):
                for list_item in r:
                    event = Event()
                    event.stanza = stanza
                    event.data = json.dumps(list_item)
                    # Tell the EventWriter to write this event
                    ew.write_event(event)
            else:
                ew.write_event(event)
                event = Event()
                event.stanza = stanza
                event.data = json.dumps(r)
                # Tell the EventWriter to write this event
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
        assert rr.is_preview == False

        return result_list


if __name__ == "__main__":
    sys.exit(MyScript().run(sys.argv))
