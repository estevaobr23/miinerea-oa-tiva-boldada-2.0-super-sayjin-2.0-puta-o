from __future__ import annotations

from typing import Any
from apify_client import ApifyClient

class ApifyRunner:
    def __init__(self, token: str):
        self.client = ApifyClient(token)

    def run(self, actor_id: str, run_input: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        actor = self.client.actor(actor_id)
        run = actor.call(run_input=run_input)
        if run is None:
            raise RuntimeError(f"Actor {actor_id} nao retornou run.")
        dataset_id = getattr(run, "default_dataset_id", None) or run.get("defaultDatasetId")
        if not dataset_id:
            raise RuntimeError(f"Actor {actor_id} terminou sem default dataset.")
        items = self.client.dataset(dataset_id).list_items(clean=True).items
        run_dict = run if isinstance(run, dict) else run.model_dump(by_alias=True)
        return run_dict, list(items)
