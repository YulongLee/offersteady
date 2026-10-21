# Build with this release directory as context; requires the immutable prior Web image locally.
FROM sha256:011d1f5de69f1208bf8b9c5b9496d4acddcbe090e6c159a0173214eb8efbbee2
COPY --chmod=0644 --chown=0:0 nginx/default.conf /etc/nginx/conf.d/default.conf
