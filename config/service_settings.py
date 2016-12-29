# Define rule priority of each service
service_priority = {
    'service_control': 65535,
    'app1': 0,
    'app2': 0,
    'app3': 0
}

# Define which table service applied rule into
service_sequence = {
    'app1': 0,
    'app2': 1,
    'app3': 2
}

# service enable or disable
service_status = {
    'app1': True,
    'app2': True,
    'app3': True
}
