"""General testing of CEF Python."""

import unittest
# noinspection PyUnresolvedReferences
import _test_runner
from os.path import basename
from cefpython3 import cefpython as cef
import time
import base64
import sys

# To show the window for an extended period of time increase this number.
MESSAGE_LOOP_RANGE = 25  # each iteration is 0.01 sec

g_browser = None
g_client_handler = None
g_external = None

g_datauri_data = """
<!DOCTYPE html>
<html>
<head>
    <style type="text/css">
    body,html {
        font-family: Arial;
        font-size: 11pt;
    }
    </style>
    <script>
    function print(msg) {
        console.log(msg+" [JS]");
        msg = msg.replace("ok", "<b style='color:green'>ok</b>");
        msg = msg.replace("error", "<b style='color:red'>error</b>");
        document.getElementById("console").innerHTML += msg+"<br>";
    }
    window.onload = function(){
        print("window.onload() ok");

        // Test binding property: test_property1
        if (test_property1 == "Test binding property to the 'window' object") {
            print("test_property_1 ok");
        } else {
            throw new Error("test_property1 contains invalid string");
        }

        // Test binding property: test_property2
        if (JSON.stringify(test_property2) == '{"key1":"Test binding property'+
                ' to the \\'window\\' object","key2":["Inside list",1,2]}') {
            print("test_property2 ok");
        } else {
            throw new Error("test_property2 contains invalid value");
        }

        // Test binding function: test_function
        test_function();
        print("test_function() ok");

        // Test binding external object and use of javascript<>python callbacks
        external.test_callbacks(function(msg_from_python, py_callback){
            if (msg_from_python == "String sent from Python") {
                print("test_callbacks() ok");
            } else {
                throw new Error("test_callbacks(): msg_from_python contains"+
                                " invalid value");
            }
            py_callback("String sent from Javascript");
            print("py_callback() ok");
        });
    };
    </script>
</head>
<body>
    <!-- FrameSourceVisitor hash = 747ef3e6011b6a61e6b3c6e54bdd2dee -->
    <h1>Main test</h1>
    <div id="console"></div>
</body>
</html>
"""
g_datauri = "data:text/html;base64,"+base64.b64encode(g_datauri_data.encode(
        "utf-8", "replace")).decode("utf-8", "replace")

g_subtests_ran = 0


def subtest_message(message):
    global g_subtests_ran
    g_subtests_ran += 1
    print(str(g_subtests_ran) + ". " + message)
    sys.stdout.flush()


class MainTest_IsolatedTest(unittest.TestCase):

    def test_main(self):
        """Main entry point."""
        # All this code must run inside one single test, otherwise strange
        # things happen.
        print("")

        # Test initialization of CEF
        cef.Initialize({
            "debug": False,
            "log_severity": cef.LOGSEVERITY_ERROR,
            "log_file": "",
        })
        subtest_message("cef.Initialize() ok")

        # Test global client callback
        global g_client_handler
        g_client_handler = ClientHandler(self)
        cef.SetGlobalClientCallback("OnAfterCreated",
                                    g_client_handler._OnAfterCreated)
        subtest_message("cef.SetGlobalClientCallback() ok")

        # Test creation of browser
        global g_browser
        g_browser = cef.CreateBrowserSync(url=g_datauri)
        self.assertIsNotNone(g_browser, "Browser object")
        subtest_message("cef.CreateBrowserSync() ok")

        # Test client handler
        g_browser.SetClientHandler(g_client_handler)
        subtest_message("browser.SetClientHandler() ok")

        # Test javascript bindings
        global g_external
        g_external = External(self)
        bindings = cef.JavascriptBindings(
                bindToFrames=False, bindToPopups=False)
        bindings.SetFunction("test_function", g_external.test_function)
        bindings.SetProperty("test_property1", g_external.test_property1)
        bindings.SetProperty("test_property2", g_external.test_property2)
        bindings.SetObject("external", g_external)
        g_browser.SetJavascriptBindings(bindings)
        subtest_message("browser.SetJavascriptBindings() ok")

        # Run message loop for 0.5 sec.
        # noinspection PyTypeChecker
        for i in range(MESSAGE_LOOP_RANGE):
            cef.MessageLoopWork()
            time.sleep(0.01)
        subtest_message("cef.MessageLoopWork() ok")

        # Test browser closing. Remember to clean reference.
        g_browser.CloseBrowser(True)
        g_browser = None
        subtest_message("browser.CloseBrowser() ok")

        # Give it some time to close before calling shutdown.
        # noinspection PyTypeChecker
        for i in range(25):
            cef.MessageLoopWork()
            time.sleep(0.01)

        # Client handler asserts and javascript External asserts
        for obj in [g_client_handler, g_external]:
            test_for_True = False  # Test whether asserts are working correctly
            for key, value in obj.__dict__.items():
                if key == "test_for_True":
                    test_for_True = True
                    continue
                if "_True" in key:
                    self.assertTrue(value, "Check assert: "+key)
                    subtest_message(obj.__class__.__name__ + "." +
                                    key.replace("_True", "") +
                                    " ok")
                elif "_False" in key:
                    self.assertFalse(value, "Check assert: "+key)
                    subtest_message(obj.__class__.__name__ + "." +
                                    key.replace("_False", "") +
                                    " ok")
            self.assertTrue(test_for_True)

        # Test shutdown of CEF
        cef.Shutdown()
        subtest_message("cef.Shutdown() ok")

        # Display real number of tests there were run
        print("\nRan " + str(g_subtests_ran) + " sub-tests in test_main")
        sys.stdout.flush()


class ClientHandler(object):
    def __init__(self, test_case):
        self.test_case = test_case
        self.frame_source_visitor = None

        # Asserts for True/False will be checked just before shutdown
        self.test_for_True = True  # Test whether asserts are working correctly
        self.OnAfterCreated_True = False
        self.OnLoadStart_True = False
        self.OnLoadEnd_True = False
        self.FrameSourceVisitor_True = False
        self.javascript_errors_False = False
        self.OnConsoleMessage_True = False

    # noinspection PyUnusedLocal
    def _OnAfterCreated(self, browser):
        self.OnAfterCreated_True = True

    # noinspection PyUnusedLocal
    def OnLoadStart(self, browser, frame):
        self.test_case.assertEqual(browser.GetUrl(), g_datauri)
        self.OnLoadStart_True = True

    # noinspection PyUnusedLocal
    def OnLoadEnd(self, browser, frame, http_code):
        self.test_case.assertEqual(http_code, 200)
        self.frame_source_visitor = FrameSourceVisitor(self, self.test_case)
        frame.GetSource(self.frame_source_visitor)
        browser.ExecuteJavascript(
                "print('ClientHandler.OnLoadEnd() ok')")
        self.OnLoadEnd_True = True

    # noinspection PyUnusedLocal
    def OnConsoleMessage(self, browser, message, source, line):
        if "error" in message.lower() or "uncaught" in message.lower():
            self.javascript_errors_False = True
            raise Exception(message)
        else:
            # Confirmation that messages from javascript are coming
            self.OnConsoleMessage_True = True
            subtest_message(message)


class FrameSourceVisitor(object):
    """Visitor for Frame.GetSource()."""

    def __init__(self, client_handler, test_case):
        self.client_handler = client_handler
        self.test_case = test_case

    # noinspection PyUnusedLocal
    def Visit(self, value):
        self.test_case.assertIn("747ef3e6011b6a61e6b3c6e54bdd2dee",
                                g_datauri_data)
        self.client_handler.FrameSourceVisitor_True = True


class External(object):
    """Javascript 'window.external' object."""

    def __init__(self, test_case):
        self.test_case = test_case

        # Test binding properties to the 'window' object.
        self.test_property1 = "Test binding property to the 'window' object"
        self.test_property2 = {"key1": self.test_property1,
                               "key2": ["Inside list", 1, 2]}

        # Asserts for True/False will be checked just before shutdown
        self.test_for_True = True  # Test whether asserts are working correctly
        self.test_function_True = False
        self.test_callbacks_True = False
        self.py_callback_True = False

    def test_function(self):
        """Test binding function to the 'window' object."""
        self.test_function_True = True

    def test_callbacks(self, js_callback):
        """Test both javascript and python callbacks."""
        def py_callback(msg_from_js):
            self.test_case.assertEqual(msg_from_js,
                                       "String sent from Javascript")
            self.py_callback_True = True
        js_callback.Call("String sent from Python", py_callback)
        self.test_callbacks_True = True


if __name__ == "__main__":
    _test_runner.main(basename(__file__))
