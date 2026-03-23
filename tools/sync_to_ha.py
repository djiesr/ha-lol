#!/usr/bin/env python3
"""
Copie custom_components/lol_stats vers Home Assistant (SSH + SCP),
puis lance « ha core restart ».

Variables d'environnement :
  HA_SSH_HOST       (obligatoire) ex. 192.168.1.108
  HA_SSH_USER       défaut : hassio
  HA_SSH_PASSWORD   mot de passe SSH (si vide : clés SSH / agent)
  HA_SKIP_RESTART   si "1" : pas de redémarrage après copie

Dépendances : pip install paramiko scp
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _repo_root() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    return Path(__file__).resolve().parent.parent


def _require(module: str):
    try:
        return __import__(module)
    except ImportError:
        print(f"Manque le module « {module} ». Installez : pip install paramiko scp", file=sys.stderr)
        raise SystemExit(1)


def main() -> None:
    paramiko = _require("paramiko")
    _require("scp")
    from scp import SCPClient

    host = os.environ.get("HA_SSH_HOST", "").strip()
    user = os.environ.get("HA_SSH_USER", "hassio").strip()
    password = os.environ.get("HA_SSH_PASSWORD")
    if password is not None:
        password = password.strip() or None
    skip_restart = os.environ.get("HA_SKIP_RESTART", "").strip() in ("1", "true", "yes")

    if not host:
        print("Définissez HA_SSH_HOST (voir ha-sync.example.env à la racine du dépôt).", file=sys.stderr)
        raise SystemExit(1)

    repo = _repo_root()
    local = repo / "custom_components" / "lol_stats"
    if not local.is_dir():
        print(f"Source introuvable : {local}", file=sys.stderr)
        raise SystemExit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kw: dict = {"hostname": host, "username": user, "timeout": 30}
    if password:
        connect_kw["password"] = password
    else:
        connect_kw["look_for_keys"] = True
        connect_kw["allow_agent"] = True

    print(f"Connexion SSH {user}@{host} …")
    client.connect(**connect_kw)

    remote_comp = "/config/custom_components"

    def run(cmd: str) -> tuple[int, str, str]:
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        code = stdout.channel.recv_exit_status()
        return code, out, err

    remote_lol = f"{remote_comp}/lol_stats"

    print("Préparation des droits sur le Pi …")
    code, out, err = run(
        f"sudo mkdir -p {remote_lol} && sudo chown -R {user}:{user} {remote_lol}"
    )
    if code != 0:
        print(err or out, file=sys.stderr)
        raise SystemExit(code)

    print("Copie des fichiers (SCP) …")
    with SCPClient(client.get_transport(), socket_timeout=120) as scp:
        scp.put(str(local), recursive=True, remote_path=f"{remote_comp}/")

    print("Remise des droits root …")
    code, out, err = run(f"sudo chown -R root:root {remote_lol}")
    if code != 0:
        print(err or out, file=sys.stderr)
        client.close()
        raise SystemExit(code)

    code, _, err = run(f"test -f {remote_lol}/manifest.json")
    if code != 0:
        print(
            "manifest.json introuvable sur le serveur après copie. "
            "Vérifiez les chemins et les droits.",
            file=sys.stderr,
        )
        if err.strip():
            print(err.strip(), file=sys.stderr)
        client.close()
        raise SystemExit(1)

    if skip_restart:
        print("HA_SKIP_RESTART=1 → pas de redémarrage.")
        client.close()
        return

    print("Redémarrage de Home Assistant Core (ha core restart) …")
    code, out, err = run("ha core restart")
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip(), file=sys.stderr)
    client.close()
    if code != 0:
        print(
            "La commande « ha core restart » a retourné un code non nul. "
            "Vérifiez que le module SSH a bien l’outil « ha ».",
            file=sys.stderr,
        )
        raise SystemExit(code)

    print("OK — redémarrage demandé (la session SSH peut se couper).")


if __name__ == "__main__":
    main()
