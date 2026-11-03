"""Pure bootstrap state evaluation; never returns Application specs or secrets."""


def conditions(obj):
    return {c.get("type"): c.get("status")
            for c in ((obj.get("status") or {}).get("conditions") or [])}


def app_ready(app):
    status = app.get("status") or {}
    return (status.get("sync", {}).get("status") == "Synced"
            and status.get("health", {}).get("status") == "Healthy"
            and not app.get("operation")
            and status.get("operationState", {}).get("phase")
            not in ("Running", "Terminating", "Failed", "Error"))


def platform_ready(pools, pods):
    if not pools or not all(conditions(p).get("Updated") == "True"
                            and conditions(p).get("Updating") == "False"
                            and conditions(p).get("Degraded") == "False" for p in pools):
        return False
    for component in ("repo-server", "application-controller"):
        if not any(component in p.get("metadata", {}).get("name", "")
                   and not p.get("metadata", {}).get("deletionTimestamp")
                   and conditions(p).get("Ready") == "True" for p in pods):
            return False
    return True


def bootstrap_state(snapshot):
    apps = snapshot.get("apps", [])
    api_ok = snapshot.get("api_ok", False)
    counts = snapshot.get("counts", {})
    poll = int(snapshot.get("poll", 0))
    limit = int(snapshot.get("max_recovery", 3))
    cooldown = int(snapshot.get("cooldown", 5))
    pending, recovery = [], []
    stable = api_ok and platform_ready(snapshot.get("pools", []), snapshot.get("pods", []))
    parent = snapshot.get("parent", {})
    evaluated = apps + ([parent] if parent and parent not in apps else [])
    for app in evaluated:
        if app_ready(app):
            continue
        meta, status = app.get("metadata", {}), app.get("status") or {}
        name = meta.get("name", "unknown")
        phase = status.get("operationState", {}).get("phase")
        health = status.get("health", {}).get("status", "Unknown")
        sync = status.get("sync", {}).get("status", "Unknown")
        pending.append({"name": name, "sync": sync, "health": health, "operation": phase or "None"})
        previous = counts.get(name, {})
        terminal = (phase in ("Failed", "Error") or health == "Degraded"
                    or (phase == "Succeeded" and sync == "OutOfSync"))
        # Do not cancel active work or retry healthy, still-starting workloads.
        if (stable and snapshot.get("platform_stable", False) and terminal
                and not app.get("operation") and phase not in ("Running", "Terminating")
                and int(previous.get("count", 0)) < limit
                and poll - int(previous.get("last_poll", -cooldown)) >= cooldown
                and (status.get("sync", {}).get("revision") or status.get("sync", {}).get("revisions"))
                and meta.get("resourceVersion")):
            candidate = {"name": name, "resource_version": meta["resourceVersion"]}
            sync_status = status["sync"]
            if sync_status.get("revisions"):
                candidate["revisions"] = sync_status["revisions"]
            else:
                candidate["revision"] = sync_status["revision"]
            recovery.append(candidate)
    parent_ready = bool(parent) and app_ready(parent)
    return {"ready": bool(stable and snapshot.get("platform_stable", False)
                          and apps and not pending and parent_ready),
            "platform_ready": bool(stable), "pending": pending,
            "parent_ready": parent_ready, "recover": recovery[:3]}


class FilterModule:
    def filters(self):
        return {"ocp5_rhacs_bootstrap_state": bootstrap_state}
