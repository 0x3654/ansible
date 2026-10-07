# mediaserver

Universal plex stack (plex + tautulli, optional frp tunnel) for the homelab hosts.
One jinja compose, host differences come from `mediaserver_role` group/host vars.

## Per-host checklist

Files to prepare ON THE HOST (not in git), relative to the stack dir:

- `<secrets>/plex.env` — linuxserver env (PLEX_CLAIM etc.), shared by plex and tautulli
- `<secrets>/media-binds.yaml` — only if `mediaserver_media_binds_extends: true`:
  `x-media-binds` service with the host's media bind mounts

In the repo:

- `vars/secrets.yml` (vault): `mediaserver_frp_tokens: {<host>: "<token>"}` — only
  for hosts with `mediaserver_frp_tunnel: true`
- inventory `mediaserver_role`: host entry + feature flags

## Flags

| Flag | micro | nano | Meaning |
|---|---|---|---|
| `mediaserver_gpu` | true | false | nvidia passthrough block (env + `deploy.resources`); needs nvidia-container-toolkit |
| `mediaserver_tsdproxy` | true | false | tsdproxy labels (plex/tautulli) |
| `mediaserver_dns` | LAN resolvers | `[]` | plex `dns:` block, omitted when empty |
| `mediaserver_media_binds_extends` | true | optional | extends from `<secrets>/media-binds.yaml` |
| `mediaserver_frp_tunnel` | true | false | frpc + tunnel-watch + frpc-guard + tunnel net |
| `mediaserver_transcode_size` | 2G | smaller | plex /transcode tmpfs |

## Architecture

Images are multi-arch (linuxserver/plex, tautulli, alpine, fatedier/frpc):
amd64 and arm64 both work with no overrides. On hosts without a GPU plex falls
back to software transcoding — size the `mediaserver_transcode_size` tmpfs to RAM.

## Volume invariant

`mediaserver_plex` / `mediaserver_tautulli` are bind-backed named volumes
(`<data_root>/plex`, `<data_root>/tautulli`). Their names derive from the compose
project name = stack directory name. **Never rename the stack directory on a live
host** — the volumes would orphan and plex would boot with an empty library.
