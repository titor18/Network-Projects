from re import match
from Router import Router
from netmiko import ConnectHandler
from templates import bfd_template

class FieldRouter(Router):
    BGP_DOWN_STATES = ("Idle", "Connect", "Active")
    ISE_SERVERS = ['10.81.89.123', '10.72.31.189', '10.78.1.115', '10.78.12.16']
    
    def __init__(self, ip_address, credentials):
        super().__init__(ip_address, credentials)


    def execute_commands(self):
        results = super().execute_commands()
        with ConnectHandler(**self.handler) as net_connect:
            results["bfd_status"] = net_connect.send_command("show bfd neighbor", use_ttp=True, ttp_template=bfd_template)
            for variable,command in Router.command_dict[1].items():
                results[variable] = net_connect.send_command(command, use_textfsm=True)
        return results


    def speed_duplex_validator(self, interface_config, if_type):
        """
        This function validates the speed and duplex configuration
        for the WAN and LAN interfaces, and adds the information to
        output_dict

        Parameters
        ----------
        if_type : str
            Type of interface to check (LAN or WAN)
        interface_config : str
            Result of the "Show running-config interface [interface ID]"

        Returns
        -------
        None
        """
        #get rid of the white spaces to make sure the script does not fail due to
        #lines like " speed 100" or "duplex full "
        interface_config = [element.strip() for element in interface_config.split('\n')]
        is_duplex_full = "duplex full" in interface_config or "no negotiation auto" in interface_config
        is_speed_set = "speed 100" in interface_config or "speed 1000" in interface_config
        speed = 1000 if "speed 1000" in interface_config else 100 if "speed 100" in interface_config else None
        Router.output_dict[f"{if_type.lower()}_interface_results"] = (
            f"The {if_type} interface speed is {'hardcoded to ' + str(speed) if is_speed_set else 'set to auto'} "
            f"and the duplex is {'hardcoded to Full' if is_duplex_full else 'set to auto'}.\n")


    def bgp_status(self, bgp_info):
        """
        This function determines the status of the current BGP
        session, and adds the information to output_dict.

        Parameters
        ----------
        bgp_info : dict
            Dictionary that contains the status information of the
            current BGP session.

        Returns
        -------
        None
        """
        bgp_uptime, bgp_state = bgp_info["up_down"], bgp_info["state_pfxrcd"]
        status = "up" if bgp_state not in FieldRouter.BGP_DOWN_STATES else "down"
        Router.output_dict["bgp_results"] = f"BGP has been {status} for over {bgp_uptime}.\n"


    def bfd_status(self, bfd_info):
        """
        This function checks wheter or not BFD is configured,
        and its current status. The formated result is then added 
        to output_dict.

        Parameters
        ----------
        bfd_info : List
            List that contains the status information of the
            current BFD session.

        Returns
        -------
        None
        """
        try:
            bfd_info = bfd_info[0][0][0]
            neighbor_address = bfd_info['neighbor_address']
            status = "UP" if bfd_info["state"] == "Up" else "DOWN"
            Router.output_dict["bfd_results"] = f"BFD neighborship with {neighbor_address} is {status}.\n"
        except:
            Router.output_dict["bfd_results"] = "BFD is not configured.\n"


    def policy_map_checker(self, pm_info, pm_interface):
        """
        This function determines if the policy map has been configured,
        and whther or not it was applied to the right interface. The formated 
        result is then added to output_dict.

        Parameters
        ----------
        pm_info : str 
            Result of the "Show policy-map" command
        pm_interface : str
            Result of the "Show policy-map interface brief" command

        Returns
        -------
        None
        """
        try:
            #if pm_info is an empty string, it's because the command did not return anything
            #we can assume that the policy map is not configured.
            if not pm_info:
                Router.output_dict["pm_results"] = "The policy map is not configured.\n"

            elif not pm_interface:
                Router.output_dict["pm_results"] = "The policy map is configured but has not been applied to an interface.\n"
            #pm_interface contains more than just the interface, so we split the content in a
            #list and search for matches with the WAN interface ID.
            elif self.wan_interface not in pm_interface.split():
                Router.output_dict["pm_results"] = (
                    f"The policy map is configured but is applied to the wrong interface ({pm_interface}). "
                    f"It should be configured on {self.wan_interface}.\n")
            else:
                Router.output_dict["pm_results"] = f"The policy map is configured and applied to {self.wan_interface}.\n"
        except Exception as e:
            Router.output_dict["pm_results"] = f"An error occurred while checking the policy map: {e}\n"


    def default_route_validator(self, default_route_info):
        """
        This function validates if a floating default route has been
        configured. The formated result is then added to output_dict.

        Parameters
        ----------
        default_route_info : str 
            Result of the "Show running-config | i ip route 0.0.0.0 0.0.0.0" command

        Returns
        -------
        None
        """
        pattern = r"^ip route 0\.0\.0\.0 0\.0\.0\.0 220$"
        match_pattern = match(pattern, default_route_info)
        result_message = (
        f"The default weighted route is properly configured ({default_route_info}).\n"
        if match_pattern
        else "The default weighted route is not configured.\n"
        )
        Router.output_dict["default_route_results"] = result_message


    def ise_servers_validator(self, server_config):
        """
        This function validates if the required ISE servers have been 
        added to the router's configuration. The formated result is then 
        added to output_dict.

        Parameters
        ----------
        server_config : str 
            Result of the "show run | i tacacs server" command

        Returns
        -------
        None
        """
        not_configured_servers = [server for server in FieldRouter.ISE_SERVERS if server not in server_config]
        result_message = (
            f"The following ISE servers are not configured: {', '.join(not_configured_servers)}\n"
            if not_configured_servers
            else f"All the ISE servers {','.join(FieldRouter.ISE_SERVERS)} have been configured.\n"
        )
        Router.output_dict["ise_results"] = result_message
