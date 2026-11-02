FROM docker.io/library/python@sha256:623674a14ef93d052bb9b0de4dbf5f28eb578a35263838941cc8aa43213c1487
WORKDIR /build
COPY archives/ /build/archives/
COPY installer/ /build/installer/
COPY wheel/ /build/wheel/
COPY explicit.txt checksums.sha256 extract_installer.py /build/
RUN sha256sum -c checksums.sha256
RUN /usr/local/bin/python -I /build/extract_installer.py
RUN /build/micromamba --no-rc --no-env --root-prefix /opt/mamba create \
    --yes --prefix /opt/inference --offline --file /build/explicit.txt
RUN /usr/local/bin/python -I -m pip --python /opt/inference/bin/python install \
    --no-index --no-deps --no-compile --disable-pip-version-check /build/wheel/autoengineering-0.2.0-py3-none-any.whl
RUN /opt/inference/bin/python -I -c "import numpy, scipy, pandas, autoengineering"
RUN mkdir -p /work && chown 1000:1000 /work && chmod 0700 /work
RUN rm -rf /build /opt/mamba
WORKDIR /work
USER 1000:1000
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV NUMEXPR_NUM_THREADS=1
ENV PYTHONNOUSERSITE=1
ENTRYPOINT []
CMD ["/opt/inference/bin/python","-I","-m","autoengineering.utility.guest_bootstrap","/work/job.json"]
