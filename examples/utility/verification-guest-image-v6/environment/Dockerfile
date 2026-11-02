FROM localhost/ae-guest-source-af0b7843f0be4a3b99f0ce85739e4676:frozen AS frozen
FROM scratch
COPY --from=frozen / /
ENV PATH="/opt/inference/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ENV LANG="C.UTF-8"
ENV OMP_NUM_THREADS="1"
ENV MKL_NUM_THREADS="1"
ENV OPENBLAS_NUM_THREADS="1"
ENV NUMEXPR_NUM_THREADS="1"
ENV PYTHONNOUSERSITE="1"
LABEL org.autoengineering.purpose="utility-frozen-routing-guest-candidate-v1"
LABEL org.autoengineering.environment="aec404431cb50f0bf3e34362183dc74294ce47b8bd96eb52241245da80b4d824"
LABEL org.autoengineering.wheel="52b76635374ca3e4c50f773aa00c4f184341f907a2bb428c277b7ae9700d86e7"
LABEL org.autoengineering.source-image="sha256:9e4a8f69e6075ac63cc8f6f70c0d26d3a4ba6b805fa81b9bab92bf19409dc065"
LABEL org.autoengineering.environment-recipe="scratch-final-v1"
WORKDIR /work
USER 1000:1000
ENTRYPOINT []
CMD ["/opt/inference/bin/python","-I","-m","autoengineering.utility.guest_bootstrap","/work/job.json"]
