"""
This script verifies that the router's configuration is in compliance 
with the required network assurance parameters, and also checks the operational
status of protocols like BGP, VRRP, and BFD.
"""
from getpass import getpass
from FieldRouter import FieldRouter
from CellRouter import CellRouter

def execute_router_commands(device):
    router_facts = device.execute_commands()
    device.format_general_info(router_facts["general_information"][0])
    device.format_environment_info(router_facts["environment_information"])
    device.format_vrrp_status(router_facts["vrrp_information"])
    device.flow_exporter_validator(router_facts["wan_config"], router_facts["flow_exporter_information"])
    device.snmp_validator(router_facts["snmp_servers_information"])
    device.acl_validator(router_facts["acls_information"])
    if isinstance(device, FieldRouter):
        device.bgp_status(router_facts["bgp_info"][0])
        device.bfd_status(router_facts["bfd_status"])
        device.policy_map_checker(router_facts["policy_map"], router_facts["policy_map_interface"])
        device.default_route_validator(router_facts["default_route"])
        device.ise_servers_validator(router_facts["tacacs_information"])
        for if_type, interface_config in [("LAN", router_facts["lan_config"]), ("WAN", router_facts["wan_config"])]:
            device.speed_duplex_validator(interface_config, if_type)
    elif isinstance(device, CellRouter):
        device.snmp_validator(router_facts["cell_levels"])

if __name__ == "__main__":
#Prompt the user for router information
    while True:
        router_type = input("""
        Please choose the type of router to check:
        1. Cellular Router
        2. Field Router
        Enter the number corresponding to your choice: """)
        if router_type in ('1', '2'):
            break
        else:
            print("Invalid input. Please enter '1' or '2'.")

    device_ip = input("Please enter the IP address of the router to check: ")
    username = input("Please enter your username: ")
    password = getpass("Please enter your password: ")
    router_class = FieldRouter if router_type == '2' else CellRouter
    router = router_class(device_ip, {"username": username, "password": password})
    
    execute_router_commands(router)
    router.file_writer(username)
