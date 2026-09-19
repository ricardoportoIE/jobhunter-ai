CREATE UNIQUE INDEX application_per_job ON records(owner_id,(data->>'job_id'))
WHERE kind='application';
