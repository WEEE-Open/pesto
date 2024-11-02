from PyQt5.QtCore import pyqtSignal, QObject
from twisted.internet.interfaces import IAddress
from twisted.internet.protocol import Protocol, ClientFactory
import json

from twisted.protocols.basic import LineOnlyReceiver


class ClientProtocol(LineOnlyReceiver):

    MAX_LENGTH = 32768  # value in bytes - Increased to avoid connection drop due to smartctl message lengths

    def __init__(self, message_received: pyqtSignal, factory):
        self.message_received = message_received
        self.factory: ConnectionFactory = factory

    def connectionMade(self):
        """Called when a connection is made to the server.

        This method is invoked when a new connection is established.
        It stores the instance of the protocol in the factory for later use and
        updates the host information with the peer's address.

        The following actions occur:
        1. Calls the `on_connection` method of the factory to signal that
           a connection has been established.
        2. Retrieves the server's address and port.
        3. Updates the host information in the factory with the server's address details.

        Raises:
            Exception: If an error occurs during the connection handling,
            the exception is caught and printed.

        Example:
            If a connection is made from the peer with host '192.168.1.10'
            and port '1030', the factory will log:
            "connection_made 192.168.1.10 1030"
        """

        try:
            self.factory.on_connection(self)
            peer = self.transport.getPeer()
            self.factory.update_host(f"connection_made {peer.host} {peer.port}")
        except Exception as e:
            print(e)

    def lineReceived(self, line):
        """Called when a line of data is received from the server.

        This method processes incoming data from the server by decoding
        it from bytes to a UTF-8 string and then passing the decoded line
        to the factory's `update_host` method for further processing.

        Args:
            line (bytes): The line of data received from the server,
            provided as a byte string.

        Raises:
            UnicodeDecodeError: If the line cannot be decoded
            to a UTF-8 string, a message is printed to indicate
            the issue, and the method returns without further action.

        The expected format of the line can vary:
        - If the line contains "connection_made", it should follow with
          the host and port, e.g., "connection_made 192.168.1.10 8080".
        - If the line indicates a lost connection, it could simply be
          "connection_lost".
        - Other lines should include a command followed by optional
          additional arguments, generally a dict.

        Example:
            If the client sends the line "connection_made 192.168.1.10 8080",
            this method will decode the line and call the factory's
            `update_host` method with it, leading to the host and port
            being updated accordingly.
        """

        try:
            line = line.decode("utf-8")
            self.factory.update_host(line)
        except UnicodeDecodeError:
            print(f"CLIENT: Oh no, UnicodeDecodeError!")
            return

    def send_msg(self, msg):
        """Sends a message to the server.

        This method checks the connection status and sends the specified
        message to the server. If the message indicates a request to
        close the connection after the current operation, it sends
        the message and disconnects from the server.

        Args:
            msg (str): The message to be sent to the server. It should
            be a string.

        If the current protocol instance is not connected (i.e., if
        `self` is None), a message is printed indicating that the
        message cannot be sent.

        If the message is "queued_close_at_end", the method will send
        this message to the server, followed by a call to disconnect
        from the server.

        Example:
            If the input message is "get_disks", this method will
            send the encoded message to the server.
            If the input message is "queued_close_at_end", the method
            will send this message and then disconnect from the server.
        """

        if self is None:
            print("CLIENT: Cannot send message to server. No connection.")
        else:
            if msg == "queued_close_at_end":
                self.sendLine(msg.encode("utf-8"))
                self.disconnect()
            else:
                self.sendLine(msg.encode("utf-8"))

    def lineLengthExceeded(self, line):
        """Handles the situation when the received line exceeds the allowed length.

        This method is called when a line of data received from the client
        exceeds the predetermined length limit. It notifies the user of the
        error and initiates a disconnection from the server.

        Args:
            line (str): The line of data that triggered the length
            violation.

        This method prints an error message to the console indicating
        that the connection is being dropped due to line length exceeding
        the limit.

        Example:
            If a line received is too long, the output will be:
            "CLIENT-ERROR: Line length exceeded (12345 characters), dropping connection."
            and the connection to the server will be closed.

        Note:
            The maximum allowed length for a line is given by MAX_LENGTH.
        """
        print(f"CLIENT-ERROR: Line length exceeded ({len(line)} characters), dropping connection.")
        self.disconnect()

    def disconnect(self):
        """Closes the connection to the server.

        This method initiates the process of disconnecting the current
        protocol instance from the server by calling the appropriate
        method on the transport layer.

        It is typically called when the protocol needs to terminate
        the connection, such as during error handling or when the
        client requests a disconnect.

        Example:
            Calling this method will result in the server being informed
            that the client is disconnecting, and the connection will
            be closed gracefully.
        """
        self.transport.loseConnection()


class ConnectionFactory(ClientFactory, QObject):
    data_received = pyqtSignal(str, str)

    protocol = ClientProtocol

    def __init__(self, parent: QObject):
        super().__init__(parent)
        self.protocol_instance: ClientProtocol = None

    def on_connection(self, protocol):
        self.protocol_instance = protocol

    def buildProtocol(self, addr: IAddress):
        return ClientProtocol(self.data_received, self)

    def startedConnecting(self, connector):
        print("CLIENT_FACTORY: Connecting.")

    def clientConnectionFailed(self, connector, reason):
        print(f"CLIENT_FACTORY: Lost connection. Reason: {reason}")
        self.data_received.emit("connection_lost")

    def clientConnectionLost(self, connector, reason):
        print(f"CLIENT_FACTORY: Lost connection. Reason: {reason}")

    def update_host(self, line: str):
        """Processes the given line to extract command and arguments, then emits the data.

        This method interprets a line of text that indicates either
        a connection status or a command, extracts data,
        and emits the corresponding command and arguments for further
        processing.

        Args:
            line (str): A line of text containing command information,
            which may indicate a connection status or other commands.

        The method processes the input line as follows:
        - If the line contains "connection_made", it splits the line
          into components to extract the host and port, then
          constructs a JSON object with this information.
        - If the line contains "connection_lost", it creates a
          JSON object indicating the loss of connection.
        - For other lines, it splits the line to separate the
          command from any additional arguments. Generally, the additional argument
          is a dict.

        Example:
            If the input line is "connection_made 192.168.1.10 1030",
            it will emit:
            cmd: "connection_made"
            args: '{"host": "192.168.1.10", "port": "1030"}'

            If the input line is "connection_lost", it will emit:
            cmd: "connection_lost"
            args: '{"connection_lost": true}'
        """

        if "connection_made" in line:
            line = line.split()
            cmd = line[0]
            host = line[1]
            port = line[2]
            args = json.dumps({"host": host, "port": port})
        elif "connection_lost" in line:
            cmd = line
            args = json.dumps({"connection_lost": True})
        else:
            parts = line.split(" ", 1)
            cmd = parts[0]
            if len(parts) > 1:
                args = parts[1]
            else:
                args = ""

        self.data_received.emit(cmd, args)