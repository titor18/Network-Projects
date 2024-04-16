from socket import gethostbyaddr
from ipaddress import ip_address as ip_module
from napalm import get_network_driver
from netmiko import ConnectHandler
#imports the templates needed to parse with ttp the commands
#that cannot be parsed with textfsm
from templates import *

class Router:
    output_dict = {}
    
    SNMP_COMMUNITIES = ['snmp-server community community1 RO SNMP_RO',
                        'snmp-server community community2 RW SNMP_RW']
    command_dict = [{
        "interface_information": "show ip int brief | e unass",
        "general_information": "show ver",
        "vrrp_information": "show vrrp brief",
        "snmp_servers_information": "show run | i snmp-server",
        "acls_information": "show ip access-list"},
        {"bgp_info": "show ip bgp summary",
        "policy_map": "show policy-map",
        "policy_map_interface": "show policy-map interface brief",
        "default_route": "show run | i ip route 0.0.0.0",
        "tacacs_information": "show run | i tacacs server"}]


    def __init__(self, ip_address, credentials) -> None:
        self.ip_address= ip_address
        self.username = credentials["username"]
        self.password = credentials["password"]
        self.handler = {"device_type": "cisco_ios", 
                        "host": self.ip_address, 
                        "username": self.username, 
                        "password": self.password}


    def get_interface_role(self, interfaces_list):
        """
        This function identifies LAN and WAN interfaces from a 
        list of router interfaces.

        Parameters
        ----------
        interfaces_list : List 
            List that contains the router's interfaces
            with their parameters.

        Returns
        -------
        None
        """
        excluded_interfaces = ("Tunnel1", "Vlan501", "Cellular0/1/0", 
                               "Gi0/0/0.501", "Gi0/0.501", "Loopback0")
        for interface in interfaces_list:
            intf_name = interface["intf"]
            if intf_name in ("Cellular0/1/0", "GigabitEthernet0/0/1"):
                self.wan_interface = intf_name
            if intf_name not in excluded_interfaces:
                if intf_name == "Vlan1" or ip_module(interface["ipaddr"]).is_private:
                    self.lan_interface = intf_name
    

    def execute_commands(self):
        """
        This function executes the commands needed to perform the configuration 
        validations.

        Args:
        None

        Returns:
        command_results : dict
            Dictionary that contains the results of the executed commands.
        """
        command_results = {}
        #get device environment facts with NAPALM
        driver_ios = get_network_driver("ios")
        device = driver_ios(hostname=self.ip_address, username=self.username, password=self.password)
        device.open()
        command_results["environment_information"] = device.get_environment()
        with ConnectHandler(**self.handler) as net_connect:
            for variable,command in Router.command_dict[0].items():
                command_results[variable] = net_connect.send_command(command, use_textfsm=True)
            Router.get_interface_role(self, command_results["interface_information"])
            command_results["lan_config"] = net_connect.send_command(f"show run interface {self.lan_interface}")
            command_results["wan_config"] = net_connect.send_command(f"show run interface {self.wan_interface}")
            command_results["flow_exporter_information"] = net_connect.send_command("show flow exporter", use_ttp=True, ttp_template=flow_template_4331)
        return command_results


    def format_general_info(self, general_facts):
        """
        This function formats the router's general information
        such as the model, hostname, and device uptime. Then adds 
        the information to output_dict.

        Args:
        general_facts : dict
            Dictionary that contains the output of the "show version" commands.

        Returns:
        None
        """
        Router.output_dict["device_info_results"] = (
        f"Cisco {general_facts['hardware'][0]}. Router {general_facts['hostname']}. Uptime {general_facts['uptime']}.\n")


    def format_environment_info(self, show_environment):
        """
        This function formats the router's environmental information
        such as: the power, temperature and fan status. Then adds 
        the information to output_dict.

        Args:
        show_environment : dict
            Dictionary that contains the output of the "show environment all" command

        Returns:
        None
        """
        power = show_environment["power"]["invalid"]["status"]
        temperature = show_environment["temperature"]["invalid"]["is_alert"]
        fans = show_environment["fans"]["invalid"]["status"]
        Router.output_dict["environment_results"] = (
        f"Power is {'normal' if  power else 'in Alert'}, "
        f"the temperature is {'normal' if temperature is False else 'High'},"
        f"and fans are {'normal' if fans else 'in alert'}.\n"
        )


    def format_vrrp_status(self, vrrp_info):
        """
        This function retrieves and formats the router's VRRP status, and then, adds 
        the information to output_dict.

        Args:
        vrrp_info : dict
            Dictionary that contains the output of the "show vrrp brief" command.

        Returns:
        None
        """
        if not vrrp_info:
            Router.output_dict["vrrp_results"] = "VRRP is not configured on this router\n"
            return

        groups_status_review = [vrrp["group"] for vrrp in vrrp_info if vrrp["state"] != "Master"]
        groups_priority_review = [vrrp["group"] for vrrp in vrrp_info if vrrp["priority"] != "100"]
        is_master = (
        "This router is the VRRP master for all the configured groups"
        if not groups_status_review
        else f"VRRP needs to be checked, this router is not master for the following groups: {', '.join(groups_status_review)}")
        is_priority_right = (
        "The priority is properly configured (Priority 100) for every group"
        if not groups_priority_review
        else f"The priority is not properly configured for the following groups: {', '.join(groups_priority_review)}")

        Router.output_dict["vrrp_results"] = f"{is_master} and {is_priority_right}.\n"
    

    def flow_exporter_validator(self, wan_config, flow_exporter):
        """
        This function retrieves and formats the flow exporter information, and then, adds 
        it to output_dict.

        Args:
        wan_config : str
            Dictionary that contains the output of the "show vrrp brief" command.
        flow_exporter : List
            List that contains the information of the configured flow exporters.

        Returns:
        None
        """
        req_exporter_qty = 2
        req_src_interface = ("Loopback0", "Vlan1")
        req_dest_port = "2055"
        req_dest_addr = (
            "10.79.126.84", "10.51.18.13",
            "10.45.35.184", "10.9.111.15")
        exporter_results = []
        if len(flow_exporter[0][0]) < req_exporter_qty:
            exporter_results.append("A flow exporter is missing. Please check")
        else:
            for exporter in flow_exporter[0][0]:
                src_int = exporter.get("source_interface")
                dest_addr = exporter.get("destination_address")
                dest_port = exporter.get("destination_port")
                exporter_results.append(f"Flow Exporter: {exporter['name']}")
                exporter_results.append(f"{'NetFlow has been applied to the WAN interface.' if 'ip flow monitor FIELD_SITES' in wan_config else 'The interface config needs verification for proper NetFlow application.'}")
                exporter_results.append(f"The source interface is {f'({src_int}) correctly configured.' if src_int in req_src_interface else 'misconfigured.'}")
                exporter_results.append(f"The destination address is {f'({dest_addr}) correctly configured.' if dest_addr in req_dest_addr else 'misconfigured.'}")
                exporter_results.append(f"The destination port is {f'({dest_port}) correctly configured.' if dest_port == req_dest_port else 'misconfigured.'}")
        Router.output_dict["flow_exporter_results"] = "\n\n".join(exporter_results) + "\n\n"


    def name_getter(ip):
        """
        This function checks if a DNS entry exists for the device that is being
        checked, then adds the information to output_dict.

        Args:
        ip : str
            IP address of the device that is being checked.

        Returns:
        None
        """
        try:
            hostname = gethostbyaddr(ip)[0]
            Router.output_dict[f"dns_results"] = f"This device is registered on the DNS server as: {hostname}.\n"
        except:
            Router.output_dict[f"dns_results"] = "No DNS entry was found for this device.\n"


    def snmp_validator(self, configured_communities):
        """
        This function checks if the required SNMP communites are configured
        in the router, formats the result, and adds it to output_dict.

        Args:
        configured_communities : str
            Output of the "show run | i snmp-server" command.

        Returns:
        None
        """
        not_configured_communities = [community for community in Router.SNMP_COMMUNITIES if community not in configured_communities]
        not_configured_communities = ','.join(not_configured_communities)
        community_result = (f"The following SNMP community strings are not configured: {not_configured_communities}\n" 
                            if not_configured_communities 
                            else "All the SNMP community strings have been configured.\n")
        Router.output_dict[f"snmp_results"] = f"{community_result}"


    def acl_validator(self, current_aces):
        """
        This function checks if the required SNMP ACLs are configured
        in the router, formats the result, and adds it to output_dict.

        Args:
        current_aces : List
            List that contains the current access control entries.

        Returns:
        None
        """
        #Required ACLs
        snmp_ro = ['10.83.34.107', '10.15.78.56', '10.15.79.51', '10.102.78.54', '10.8.96.53', 
                   '10.85.51.52', '10.96.42.51', '10.17.78.60', '10.102.35.67', '10.89.72.48', '10.92.202.4']
        snmp_rw = ['10.85.51.52', '10.96.42.51', '10.17.78.60', '10.102.35.67', '10.89.72.48', 
                   '10.97.71.50', '10.84.20.31', '10.41.23.58', '10.75.89.63']
        #Checks if the current ACEs are in the required list, if so, those IPs will be removed from
        #the corresponding list. At the end, it assumes that if the lists are empty, it's because
        #the required IPs are in the ACLs.
        for acl in current_aces:
            if acl["acl_name"] == 'SNMP_RO' and acl['src_host'] in snmp_ro:
                snmp_ro.remove(acl['src_host'])
            elif acl["acl_name"] == 'SNMP_RW' and acl['src_host'] in snmp_rw:
                snmp_rw.remove(acl['src_host'])
        ro_acl_result = (f"The SNMP RO ACL has been added to this device.\n\n" if len(snmp_ro) == 0 else "The SNMP "
                        f"RO ACL has not been added to this device. The following IPs {snmp_ro} are missing.\n\n")
        rw_acl_result = (f"The SNMP RW ACL has been added to this device.\n\n" if len(snmp_rw) == 0 else "The SNMP RW "
                        f"ACL has not been added to this device. The following IPs {snmp_rw} are missing.\n\n")
        Router.output_dict["acl_results"] = f"{ro_acl_result}{rw_acl_result}"


    def file_writer(self, username):
        """
        This function writes a .txt file that contains the
        result of the configuration checks.

        Args:
        username : str
            Username of the person performing the checks.

        Returns:
        None
        """
        with open(f"C:\\Users\\{username}\\Desktop\\router_site_review.txt", "w", encoding="UTF-8") as writer_element:
            for result in Router.output_dict.values():
                writer_element.write(f"{result}\n")

