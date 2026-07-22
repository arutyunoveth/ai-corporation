from src.modules.customer_pilot.input_resolver import CustomerRunInputs


def test_customer_run_inputs_keeps_server_owned_identity_order():
    value = CustomerRunInputs("0379100000726000101", [], ["a", "b"], [], [])
    assert value.source_document_ids == ["a", "b"]
