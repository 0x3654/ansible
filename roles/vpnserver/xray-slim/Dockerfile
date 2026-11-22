# xray-slim: official xray-core binary without the geodata ballast.
# Our config keeps routing geo-free (private ranges as literal CIDRs),
# so the 181MB of geoip/geosite .dat files is dead weight on every host.
# The official image is distroless (no shell/coreutils), so stripping is
# done by copying only the binary onto a pinned alpine base.
# Bump BOTH digests together with vpnserver_xray_image.
FROM ghcr.io/xtls/xray-core:26.11.9@sha256:d42420dca2014cbd06e24daad8a039b455b7d9e905cda1cf871254cfffda2149 AS xray

FROM alpine:3.21@sha256:ee16d92f96db08d9d2d07da48555a27f3a69d8f0759021dbc601195ed0d2b5bd

COPY --from=xray /usr/local/bin/xray /usr/local/bin/xray
COPY --from=xray /usr/local/etc/xray /usr/local/etc/xray

ARG GIT_REV=unknown
ARG SOURCE_REPOSITORY=https://github.com/0x3654/vpnserver
LABEL org.opencontainers.image.title="vpnserver-xray-slim" \
      org.opencontainers.image.description="xtls/xray-core without unused geodata (~49MB vs 219MB)" \
      org.opencontainers.image.source="${SOURCE_REPOSITORY}" \
      org.opencontainers.image.revision="${GIT_REV}"

USER 65532:65532
ENTRYPOINT ["/usr/local/bin/xray"]
CMD ["run", "-c", "/etc/xray/config.json"]
