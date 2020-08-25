import pytest

from aws_lambda_powertools.utilities.batch import PartialSQSProcessor


@pytest.fixture(scope="module")
def sqs_event():
    return {
        "messageId": "059f36b4-87a3-44ab-83d2-661975830a7d",
        "receiptHandle": "AQEBwJnKyrHigUMZj6rYigCgxlaS3SLy0a",
        "body": "",
        "attributes": {},
        "messageAttributes": {},
        "md5OfBody": "e4e68fb7bd0e697a0ae8f1bb342846b3",
        "eventSource": "aws:sqs",
        "eventSourceARN": "arn:aws:sqs:us-east-2:123456789012:my-queue",
        "awsRegion": "us-east-1",
    }


def test_partial_sqs_get_queue_url_with_records(mocker, sqs_event):
    expected_url = "https://queue.amazonaws.com/123456789012/my-queue"

    records_mock = mocker.patch.object(PartialSQSProcessor, "records", create=True, new_callable=mocker.PropertyMock)
    records_mock.return_value = [sqs_event]

    result = PartialSQSProcessor().get_queue_url()
    assert result == expected_url


def test_partial_sqs_get_queue_url_without_records():
    assert PartialSQSProcessor().get_queue_url() is None


def test_partial_sqs_get_entries_to_clean_with_success(mocker, sqs_event):
    expected_entries = [{"Id": sqs_event["messageId"], "ReceiptHandle": sqs_event["receiptHandle"]}]

    success_messages_mock = mocker.patch.object(
        PartialSQSProcessor, "success_messages", new_callable=mocker.PropertyMock
    )
    success_messages_mock.return_value = [sqs_event]

    result = PartialSQSProcessor().get_entries_to_clean()

    assert result == expected_entries


def test_partial_sqs_get_entries_to_clean_without_success(mocker):
    expected_entries = []

    success_messages_mock = mocker.patch.object(
        PartialSQSProcessor, "success_messages", new_callable=mocker.PropertyMock
    )
    success_messages_mock.return_value = []

    result = PartialSQSProcessor().get_entries_to_clean()

    assert result == expected_entries


def test_partial_sqs_process_record_success(mocker):
    expected_value = mocker.sentinel.expected_value

    success_result = mocker.sentinel.success_result
    record = mocker.sentinel.record

    handler_mock = mocker.patch.object(PartialSQSProcessor, "handler", create=True, return_value=success_result)
    success_handler_mock = mocker.patch.object(PartialSQSProcessor, "success_handler", return_value=expected_value)

    result = PartialSQSProcessor()._process_record(record)

    handler_mock.assert_called_once_with(record)
    success_handler_mock.assert_called_once_with(record, success_result)

    assert result == expected_value


def test_partial_sqs_process_record_failure(mocker):
    expected_value = mocker.sentinel.expected_value

    failure_result = Exception()
    record = mocker.sentinel.record

    handler_mock = mocker.patch.object(PartialSQSProcessor, "handler", create=True, side_effect=failure_result)
    failure_handler_mock = mocker.patch.object(PartialSQSProcessor, "failure_handler", return_value=expected_value)

    result = PartialSQSProcessor()._process_record(record)

    handler_mock.assert_called_once_with(record)
    failure_handler_mock.assert_called_once_with(record, failure_result)

    assert result == expected_value


def test_partial_sqs_prepare(mocker):
    processor = PartialSQSProcessor()

    success_messages_mock = mocker.patch.object(processor, "success_messages", spec=list)
    failed_messages_mock = mocker.patch.object(processor, "fail_messages", spec=list)

    processor._prepare()

    success_messages_mock.clear.assert_called_once()
    failed_messages_mock.clear.assert_called_once()


def test_partial_sqs_clean(monkeypatch, mocker):
    processor = PartialSQSProcessor()
    records = [mocker.sentinel.record]

    monkeypatch.setattr(processor, "fail_messages", records)
    monkeypatch.setattr(processor, "success_messages", records)

    queue_url_mock = mocker.patch.object(PartialSQSProcessor, "get_queue_url")
    entries_to_clean_mock = mocker.patch.object(PartialSQSProcessor, "get_entries_to_clean")

    queue_url_mock.return_value = mocker.sentinel.queue_url
    entries_to_clean_mock.return_value = mocker.sentinel.entries_to_clean

    client_mock = mocker.patch.object(processor, "client", autospec=True)

    processor._clean()

    client_mock.delete_message_batch.assert_called_once_with(
        QueueUrl=mocker.sentinel.queue_url, Entries=mocker.sentinel.entries_to_clean
    )