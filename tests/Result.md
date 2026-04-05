# Integration Test Results Summary

Source run summary: 34 passed, 14 xfailed in 76.94s.

| P_VALUE | TC | Test Instance | Result | XFAIL Reason |
| --- | --- | --- | --- | --- |
| 0 | TC_01 | test_tc01_user_integration[0-user_data0] | Pass | |
| 0 | TC_01 | test_tc01_user_integration[0-user_data1] | Pass | |
| 0 | TC_01 | test_tc01_user_integration[0-user_data2] | Pass | |
| 0 | TC_01 | test_tc01_user_integration[0-user_data3] | Pass | |
| 0 | TC_02 | test_tc02_order_integration[0-order_row0] | Pass | |
| 0 | TC_02 | test_tc02_order_integration[0-order_row1] | Pass | |
| 0 | TC_02 | test_tc02_order_integration[0-order_row2] | Pass | |
| 0 | TC_02 | test_tc02_order_status_put_and_get[0] | XFail | Known upstream bug: order-service PUT handlers are defined without the route id parameter. |
| 0 | TC_03 | test_tc03_user_update_propagation[0-new_emails0-new_address0] | XFail | Known upstream bug: user-service-v2 PUT handler is defined without the route id parameter. |
| 0 | TC_03 | test_tc03_user_update_propagation[0-new_emails1-None] | XFail | Known upstream bug: user-service-v2 PUT handler is defined without the route id parameter. |
| 0 | TC_03 | test_tc03_user_update_propagation[0-None-new_address2] | XFail | Known upstream bug: user-service-v2 PUT handler is defined without the route id parameter. |
| 0 | TC_03 | test_tc03_user_update_invalid_payload[0-invalid_payload0] | XFail | Known upstream bug: user-service-v2 PUT handler is defined without the route id parameter. |
| 0 | TC_03 | test_tc03_user_update_invalid_payload[0-invalid_payload1] | XFail | Known upstream bug: user-service-v2 PUT handler is defined without the route id parameter. |
| 0 | TC_03 | test_tc03_user_update_invalid_payload[0-invalid_payload2] | XFail | Known upstream bug: user-service-v2 PUT handler is defined without the route id parameter. |
| 0 | TC_03 | test_tc03_user_update_invalid_payload[0-invalid_payload3] | XFail | Known upstream bug: user-service-v2 PUT handler is defined without the route id parameter. |
| 0 | TC_04 | test_tc04_gateway_routing_behavior[0] | Pass | |
| 50 | TC_01 | test_tc01_user_integration[50-user_data0] | Pass | |
| 50 | TC_01 | test_tc01_user_integration[50-user_data1] | Pass | |
| 50 | TC_01 | test_tc01_user_integration[50-user_data2] | Pass | |
| 50 | TC_01 | test_tc01_user_integration[50-user_data3] | Pass | |
| 50 | TC_02 | test_tc02_order_integration[50-order_row0] | Pass | |
| 50 | TC_02 | test_tc02_order_integration[50-order_row1] | Pass | |
| 50 | TC_02 | test_tc02_order_integration[50-order_row2] | Pass | |
| 50 | TC_02 | test_tc02_order_status_put_and_get[50] | XFail | Known upstream bug: order-service PUT handlers are defined without the route id parameter. |
| 50 | TC_03 | test_tc03_user_update_propagation[50-new_emails0-new_address0] | XFail | Known upstream bug: user-service-v2 PUT handler is defined without the route id parameter. |
| 50 | TC_03 | test_tc03_user_update_propagation[50-new_emails1-None] | Pass | |
| 50 | TC_03 | test_tc03_user_update_propagation[50-None-new_address2] | XFail | Known upstream bug: user-service-v2 PUT handler is defined without the route id parameter. |
| 50 | TC_03 | test_tc03_user_update_invalid_payload[50-invalid_payload0] | Pass | |
| 50 | TC_03 | test_tc03_user_update_invalid_payload[50-invalid_payload1] | XFail | Known upstream bug: user-service-v2 PUT handler is defined without the route id parameter. |
| 50 | TC_03 | test_tc03_user_update_invalid_payload[50-invalid_payload2] | Pass | |
| 50 | TC_03 | test_tc03_user_update_invalid_payload[50-invalid_payload3] | XFail | Known upstream bug: user-service-v2 PUT handler is defined without the route id parameter. |
| 50 | TC_04 | test_tc04_gateway_routing_behavior[50] | Pass | |
| 100 | TC_01 | test_tc01_user_integration[100-user_data0] | Pass | |
| 100 | TC_01 | test_tc01_user_integration[100-user_data1] | Pass | |
| 100 | TC_01 | test_tc01_user_integration[100-user_data2] | Pass | |
| 100 | TC_01 | test_tc01_user_integration[100-user_data3] | Pass | |
| 100 | TC_02 | test_tc02_order_integration[100-order_row0] | Pass | |
| 100 | TC_02 | test_tc02_order_integration[100-order_row1] | Pass | |
| 100 | TC_02 | test_tc02_order_integration[100-order_row2] | Pass | |
| 100 | TC_02 | test_tc02_order_status_put_and_get[100] | XFail | Known upstream bug: order-service PUT handlers are defined without the route id parameter. |
| 100 | TC_03 | test_tc03_user_update_propagation[100-new_emails0-new_address0] | Pass | |
| 100 | TC_03 | test_tc03_user_update_propagation[100-new_emails1-None] | Pass | |
| 100 | TC_03 | test_tc03_user_update_propagation[100-None-new_address2] | Pass | |
| 100 | TC_03 | test_tc03_user_update_invalid_payload[100-invalid_payload0] | Pass | |
| 100 | TC_03 | test_tc03_user_update_invalid_payload[100-invalid_payload1] | Pass | |
| 100 | TC_03 | test_tc03_user_update_invalid_payload[100-invalid_payload2] | Pass | |
| 100 | TC_03 | test_tc03_user_update_invalid_payload[100-invalid_payload3] | Pass | |
| 100 | TC_04 | test_tc04_gateway_routing_behavior[100] | Pass | |
