CREATE UNIQUE INDEX submission_workflow_per_application
    ON records(owner_id,(data->>'application_id')) WHERE kind='submission_workflow';
CREATE UNIQUE INDEX sandbox_receipt_per_application
    ON records(owner_id,(data->>'application_id')) WHERE kind='sandbox_receipt';
