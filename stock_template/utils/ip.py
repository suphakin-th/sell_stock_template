def get_client_ip(request):
    if request is None:
        return None

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# def check_ip(ip):
#     import ipaddress
#     from config.models import Config

#     ip_table_allow = Config.pull_value('config-ip-table-allow')
#     if ip_table_allow[0] == '':
#         return True
#     else:
#         for allow in ip_table_allow:
#             if allow:
#                 if ipaddress.ip_address(ip) in ipaddress.ip_network(allow):
#                     return True
#         return False
