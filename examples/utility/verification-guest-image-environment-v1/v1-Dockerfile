FROM localhost/ae-guest-source-b6da196193494559afeb490c8893755c:frozen AS frozen
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
LABEL org.autoengineering.environment="7c66ecada3955ad940d07fcf409b7f78bf68fc643950340f408d9d398a6fa06e"
LABEL org.autoengineering.wheel="8d693b02719c1325d7f82ac674e35418e1ab1962bbf1db475211558284b64977"
LABEL org.autoengineering.source-image="sha256:fc19692dff41a699600f76a79a97ed6cdcdf927f28e09984a79f33dcee46c399"
LABEL org.autoengineering.environment-recipe="scratch-final-v1"
WORKDIR /work
USER 1000:1000
ENTRYPOINT []
CMD ["/opt/inference/bin/python","-I","-m","autoengineering.utility.guest_bootstrap","/work/job.json"]
