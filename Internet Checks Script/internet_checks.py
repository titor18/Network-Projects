"""Internet checks automation script

This script creates a .txt file that contains the current internet checks using a
template in compliance with the one published in the XXXX folder as of xx/xx/xx. The 
file will be saved to the desktop.

This script requires the libraries below to be installed in the Python environment where 
it will be executed.
"""
from getpass import getpass
from datetime import datetime
from itertools import islice
from netmiko import ConnectHandler
from netmiko.exceptions import NetMikoAuthenticationException, NetmikoTimeoutException

#The script contains generic variables that will have to be modified in order to be used.

#The mgmt IP corresponds to the actual device IP address, while the rest are the IPs of those
#interface's BGP neighbors
REQUIRED_INTERFACES_DICT = {
                            'Internetr1': {"mgmt_interface":'x.x.x.x',
                                                    'TenGigabitEthernet0/1/0':'',
                                                    'TenGigabitEthernet0/2/0':'x.x.x.x',
                                                    'Tunnel1':'x.x.x.x',
                                                    'Tunnel1 ':'x.x.x.x',
                                                    'Tunnel21': '',
                                                    'Tunnel22': ''},
                            'Internetr2': {"mgmt_interface":'x.x.x.x',
                                                    'TenGigabitEthernet0/1/0' : '',
                                                    'TenGigabitEthernet0/2/0': 'x.x.x.x',
                                                    'Tunnel1': '',
                                                    'Tunnel10': '',
                                                    'Tunnel21': '',
                                                    'Tunnel22': ''}}
SP_LIST = ["ISP1", "ISP2"]
TO_MEGABITS = 1000000
BGP_DOWN_STATES = ["Idle", "Connect", "Active"]

def send_commands():
    """Creates the SSH handler, and executes the required commands

    Parameters
    ----------
    No parameters are received by this function

    Returns
    -------
    command_results (dict) = A dictionary with the results of the commands that were
    executed
    """

    command_results = {}

    device_handler = {
        "device_type": "cisco_ios",
        "host": device_ip,
        "username": username,
        "password": password}
    
    try:
        with ConnectHandler(**device_handler) as net_connect:
            command_results["show_interfaces"] = net_connect.send_command("show interface", use_textfsm=True)
            command_results["bgp_summary"] = net_connect.send_command("show ip bgp summary", use_textfsm=True)
            command_results["hostname"] = (net_connect.send_command("show version", use_textfsm=True))[0]["hostname"]
            command_results["hsrp_status"] = (net_connect.send_command("show standby", use_textfsm=True))[0]["state"]
            net_connect.send_command("terminal shell")
            command_results["logs"] = net_connect.send_command("show log | grep -E -i 'BGP|%LINEPROTO-5-UPDOWN' | tail 10")
    except NetMikoAuthenticationException:
        print(f"There has been a problem authenticating to {device}. Please try again")
    except NetmikoTimeoutException:
        print(f"A connection to {device} could not be established. It appears to be down")
    except Exception as e:
        print(f"An unexpected error has occurred:{e}. Please contact the script owner")
    
    return command_results


def utilization(show_interfaces):
    """This function retrieves and formats the utilization of the WAN and
    tunnel interfaces specified in REQUIRED_INTERFACES_LIST

    Parameters
    ----------
    show_interfaces : list
        List that contains the output of the "Show interfaces" command

    Returns
    -------
    utilization_result : str
        String that contains the utilization information in the template format.
    """
    utilization_result = ''
    #makes a list with the 2nd to the last interface contained on REQUIRED_INTERFACES_DICT
    interfaces =  list(islice(REQUIRED_INTERFACES_DICT[hostname].keys(), 2, None))
    for interface in show_interfaces:
        if interface["interface"] in interfaces:
            input_rate = int(interface['input_rate']) / TO_MEGABITS
            output_rate = int(interface['output_rate']) / TO_MEGABITS
            if interface["interface"] == interfaces[0]:
                utilization_result += f"""WAN Interface Inbound utilization = {input_rate}Mbps, Outbound utilization = {output_rate}Mbps. \n"""
            else:
                utilization_result +=f" {interface['interface']} Inbound utilization = {input_rate}Mbps, Outbound utilization = {output_rate}Mbps. \n"
    return utilization_result


def status_and_errors(show_interfaces):
    """This function retrieves and formats the status and error count of the 
    WAN interface and the interface that connects to the core firewalls.

    Parameters
    ----------
    show_interfaces : list
        List that contains the output of the "Show interfaces" command

    Returns
    -------
    status_result : str
        String that contains the status and error count information in the template format.
    """

    interfaces =  list(islice(REQUIRED_INTERFACES_DICT[hostname].keys(),1,3))
    status_result = ''
    for interface in show_interfaces:
        interface_name = interface['interface']
        interface_link_status = interface['link_status']
        if interface["interface"] == interfaces[0]:
            status_result += f"{interface_name} to {'FWL1' if hostname == list(REQUIRED_INTERFACES_DICT.keys())[0] else 'FWL2'} - {interface_link_status} and {int(interface['input_errors'])+int(interface['output_errors'])} Errors. \n"
        elif interface["interface"] == interfaces[1]:
            status_result += f"{interface_name} WAN interface - {interface_link_status} and {int(interface['input_errors'])+int(interface['output_errors'])} Errors. \n"
    return status_result


def bgp_information(bgp_summary):
    """This function checks and formats the status and uptime of the BGP sessions.

    Parameters
    ----------
    bgp_summary : list
        List that contains the ouput of the "Show ip bgp summary" command.

    Returns
    -------
    bgp_result : str
        String that contains the BGP status in the template format.
    """
    bgp_result = ''
    required_interfaces = REQUIRED_INTERFACES_DICT[hostname]
    for key,value in required_interfaces.items():
        for neighbor in bgp_summary:
            neighbor_ip = neighbor["bgp_neigh"]
            bgp_state = neighbor['state_pfxrcd']
            bgp_uptime = neighbor['up_down']
            if neighbor_ip == value:
                bgp_result += f"{'WAN interface' if key == 'TenGigabitEthernet0/2/0' else key} {neighbor_ip} - {'up' if bgp_state not in BGP_DOWN_STATES else 'down'} for over {bgp_uptime}. \n"
    return bgp_result


def tunnel_status(show_interfaces):
    """This function checks and formats the status of the tunnel interfaces.

    Parameters
    ----------
    show_interfaces : list
        List that contains the output of the "Show interfaces" command

    Returns
    -------
    tunnel_result : str
        String that contains the tunnel interface status in the template format.
    """
    tunnel_result = ''
    for interface in show_interfaces:
        interface_name = interface["interface"]
        if interface_name in ("Tunnel21", "Tunnel22"):
            interface_ip = interface['ip_address']
            interface_link_status = interface['link_status']
            tunnel_result += f"{interface_name} \n {interface_ip} {interface_link_status} \n"
    return tunnel_result


def txt_writer(result_list):
    """
    This function creates a .txt file and copies the data contained in result_list.

    Parameters:
    result_list : list
        List that contains the results of the functions previously executed.

    Returns:
        None
    """
    current_time = datetime.now()
    with open(f"C:\\Users\\{username}\\Desktop\\Internet_checks.txt", "w", encoding="UTF-8") as file:
        for i in range(2):
            device_name = list(REQUIRED_INTERFACES_DICT.keys())[i]
            lines_to_write = [f"{device_name} - {SP_LIST[i]} as of {current_time.strftime('%H:%M')} EST: {device_name} is {result_list[0][i]}.\n",
                              f"{result_list[1][i]}\n", 
                              f"BGP Status:\n{result_list[2][i]}\n", 
                              f"{result_list[3][i]}\n", 
                              f"Utilization:\n{result_list[4][i]}\n", 
                              f"Last 10 logs:\n{result_list[5][i]}\n", 
                              f'{"/"*80}\n']
            for line in lines_to_write:
                file.write(line)


if __name__ == '__main__':
    result_list = [[],[],[],[],[],[]]
    username = input("Enter your username: ")
    password = getpass()
    for device in REQUIRED_INTERFACES_DICT:
        device_ip = REQUIRED_INTERFACES_DICT[device]["mgmt_interface"]
        output = send_commands()
        hostname = output["hostname"]
        interfaces_status = status_and_errors(output["show_interfaces"])
        bgp = bgp_information(output["bgp_summary"])
        tunnels_result= tunnel_status(output["show_interfaces"])
        utilization_result = utilization(output["show_interfaces"])
        writing_list = [output["hsrp_status"], interfaces_status, bgp, 
                       tunnels_result, utilization_result, output["logs"]]
        for formated_line in writing_list:
            result_list[writing_list.index(formated_line)].append(formated_line)
    txt_writer(result_list)