from rq import Queue

JOB_TIMEOUT_SECONDS = 10 * 60


def enqueue(queue: Queue, job_id: str, input_key: str) -> None:
    # By import path: the runner (step 1.7) pulls in the ML stack, which the API must not load.
    queue.enqueue(
        "app.jobs.run.run_job", job_id, input_key, job_id=job_id, job_timeout=JOB_TIMEOUT_SECONDS
    )
