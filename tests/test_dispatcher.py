"""Tests for message routing and liveness in pytuya.device (protocol 3.3 frames)."""
import asyncio
import json
from functools import partial

import pytest
import pytest_asyncio

from pytuya import device
from pytuya.cipher import AESCipher
from pytuya.constants import (
    CMD_CONTROL,
    CMD_DP_QUERY,
    CMD_HEART_BEAT,
    CMD_STATUS,
    PROTOCOL_3X_HEADER_PAD,
    VERSION_33,
)
from pytuya.protocol import pack_message, parse_header

LOCAL_KEY = "0123456789abcdef"
DEVICE_ID = "bf0123456789abcdefgh"


class FakeTransport:
    def __init__(self):
        self.sent = []
        self.closed = False

    def write(self, data):
        self.sent.append(parse_header(data))

    def is_closing(self):
        return self.closed

    def close(self):
        self.closed = True


class RecordingListener(device.TuyaListener):
    def __init__(self):
        self.updates = []

    def status_updated(self, status):
        self.updates.append(dict(status))

    def disconnected(self):
        pass


def device_frame(seqno, cmd, dps=None, retcode=None, version_header=False):
    """Build a frame as a protocol 3.3 device would send it."""
    payload = b""
    if dps is not None:
        body = json.dumps({"devId": DEVICE_ID, "dps": dps, "t": 1}).encode()
        payload = AESCipher(LOCAL_KEY.encode()).encrypt_ecb(body, pad=True)
        if version_header:
            payload = VERSION_33 + PROTOCOL_3X_HEADER_PAD + payload
    if retcode is not None:
        payload = retcode.to_bytes(4, "big") + payload
    return pack_message(seqno, cmd, payload, LOCAL_KEY.encode(), 3.3, encrypt=False)


def status_push(seqno, dps):
    return device_frame(seqno, CMD_STATUS, dps, version_header=True)


@pytest_asyncio.fixture
async def proto():
    loop = asyncio.get_running_loop()
    listener = RecordingListener()
    protocol = device.TuyaProtocol(DEVICE_ID, LOCAL_KEY, 3.3, False, loop.create_future(), listener)
    protocol.transport = FakeTransport()
    protocol.test_listener = listener
    yield protocol
    if protocol._confirm_task:
        protocol._confirm_task.cancel()


async def next_request(protocol, count=1):
    """Wait until the protocol has written `count` frames and return the last header."""
    for _ in range(200):
        if len(protocol.transport.sent) >= count:
            return protocol.transport.sent[count - 1]
        await asyncio.sleep(0.005)
    raise AssertionError("no request was sent")


@pytest.mark.asyncio
async def test_status_push_does_not_change_request_seqno(proto):
    before = proto.seqno
    proto.data_received(status_push(41, {"1": False}))
    assert proto.seqno == before
    assert proto.test_listener.updates == [{"1": False}]


@pytest.mark.asyncio
async def test_status_push_sharing_seqno_with_control_reaches_listener(proto):
    task = asyncio.create_task(proto.set_dp(True, 1))
    request = await next_request(proto)
    assert request.cmd == CMD_CONTROL

    # The device's own counter happens to equal the pending request's seqno,
    # and its report arrives before the ACK.
    proto.data_received(status_push(request.seqno, {"1": True}))
    proto.data_received(device_frame(request.seqno, CMD_CONTROL, retcode=0))

    await asyncio.wait_for(task, 1)
    assert proto.test_listener.updates[-1] == {"1": True}


@pytest.mark.asyncio
async def test_unrelated_reply_with_matching_seqno_is_not_taken_as_ack(proto):
    task = asyncio.create_task(proto.set_dp(True, 1))
    request = await next_request(proto)

    proto.data_received(device_frame(request.seqno, CMD_HEART_BEAT, retcode=0))
    await asyncio.sleep(0)
    assert not task.done()

    proto.data_received(device_frame(request.seqno, CMD_CONTROL, retcode=0))
    await asyncio.wait_for(task, 1)


@pytest.mark.asyncio
async def test_status_reply_to_query_still_answers_query(proto):
    task = asyncio.create_task(proto.status())
    request = await next_request(proto)
    assert request.cmd == CMD_DP_QUERY

    proto.data_received(status_push(request.seqno, {"1": True, "20": 2301}))

    result = await asyncio.wait_for(task, 1)
    assert result["dps"] == {"1": True, "20": 2301}
    assert proto.test_listener.updates[-1] == {"1": True, "20": 2301}


@pytest.mark.asyncio
async def test_control_ack_carrying_dps_notifies_listener(proto):
    task = asyncio.create_task(proto.set_dp(False, 1))
    request = await next_request(proto)

    proto.data_received(device_frame(request.seqno, CMD_CONTROL, {"1": False}, retcode=0))

    await asyncio.wait_for(task, 1)
    assert proto.test_listener.updates == [{"1": False}]


@pytest.mark.asyncio
async def test_status_is_queried_when_device_does_not_report_after_control(proto, monkeypatch):
    monkeypatch.setattr(device, "CONTROL_CONFIRM_DELAY", 0.01)

    task = asyncio.create_task(proto.set_dp(True, 1))
    control = await next_request(proto)
    proto.data_received(device_frame(control.seqno, CMD_CONTROL, retcode=0))
    await asyncio.wait_for(task, 1)
    assert proto.test_listener.updates == []

    query = await next_request(proto, 2)
    for _ in range(50):
        if query.seqno in proto.dispatcher.listeners:
            break
        await asyncio.sleep(0.01)
    assert query.cmd == CMD_DP_QUERY
    proto.data_received(device_frame(query.seqno, CMD_DP_QUERY, {"1": True}, retcode=0))

    for _ in range(50):
        if proto.test_listener.updates:
            break
        await asyncio.sleep(0.01)
    assert proto.test_listener.updates == [{"1": True}]


@pytest.mark.asyncio
async def test_no_status_query_when_device_reports_after_control(proto, monkeypatch):
    monkeypatch.setattr(device, "CONTROL_CONFIRM_DELAY", 0.01)

    task = asyncio.create_task(proto.set_dp(True, 1))
    control = await next_request(proto)
    proto.data_received(device_frame(control.seqno, CMD_CONTROL, retcode=0))
    await asyncio.wait_for(task, 1)
    proto.data_received(status_push(7, {"1": True}))

    await asyncio.sleep(0.05)
    assert len(proto.transport.sent) == 1


@pytest.mark.asyncio
async def test_heartbeat_without_reply_raises(proto):
    proto.dispatcher.wait_for = partial(proto.dispatcher.wait_for, timeout=0.01)
    with pytest.raises(asyncio.TimeoutError):
        await proto.heartbeat()


@pytest.mark.asyncio
async def test_other_commands_without_reply_still_return_none(proto):
    proto.dispatcher.wait_for = partial(proto.dispatcher.wait_for, timeout=0.01)
    assert await proto.status() is None


@pytest.mark.asyncio
async def test_heartbeat_loop_disconnects_silent_device(proto, monkeypatch):
    monkeypatch.setattr(device, "HEARTBEAT_INTERVAL", 0)
    proto.dispatcher.wait_for = partial(proto.dispatcher.wait_for, timeout=0.01)

    proto.start_heartbeat()
    await asyncio.wait_for(proto.heartbeater, 1)

    heartbeats = [h for h in proto.transport.sent if h.cmd == CMD_HEART_BEAT]
    assert len(heartbeats) == 5
    assert proto.transport.closed
