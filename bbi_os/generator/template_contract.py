REQUIRED_TEMPLATE_FIELDS = {
    "name": str,
    "version": str,
    "architecture": dict,
    "rules": list,
    "future_modules": list,
}

REQUIRED_ARCHITECTURE_FIELDS = {
    "api_layer": dict,
    "router_layer": dict,
    "service_layer": dict,
    "state_layer": dict,
    "endpoints": list,
}
