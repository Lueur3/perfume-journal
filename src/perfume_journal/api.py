from fastapi import FastAPI, HTTPException, status

from perfume_journal.models import Perfume, PerfumeCreate
from perfume_journal.perfume_store import DuplicatePerfumeError, PerfumeStore

_store = PerfumeStore()

app = FastAPI(title="Perfume Journal")


@app.post("/perfumes", response_model=Perfume, status_code=status.HTTP_201_CREATED)
def create_perfume(body: PerfumeCreate) -> Perfume:
    try:
        return _store.create(body)
    except DuplicatePerfumeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
