from prometheus_fastapi_instrumentator import Instrumentator, metrics

instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=False,
    should_instrument_requests_inprogress=True,
    excluded_handlers=[".*admin.*", "/metrics"],
    inprogress_name="inprogress",
    inprogress_labels=True,
)

instrumentator.add(
    metrics.request_size(
        should_include_handler=True,
        should_include_method=False,
        should_include_status=True,
      
    )
).add(
    metrics.response_size(
        should_include_handler=True,
        should_include_method=False,
        should_include_status=True,
       
    )
).add(
    metrics.latency(
        should_include_handler=True,
        should_include_method=False,
        should_include_status=True,
        
    )
).add(
    metrics.requests(
        should_include_handler=True,
        should_include_method=False,
        should_include_status=True,
       
    )
).add(
    metrics.combined_size(
        should_include_handler=True,
        should_include_method=False,
        should_include_status=True,
        
    )
)
