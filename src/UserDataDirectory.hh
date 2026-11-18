#pragma once

#include <string>

// Directory for per-user state that newserv writes: players/, licenses/, teams/. Shipped data stays in system/.
// Set from --data-dir before the server loads accounts or teams; the default matches upstream's layout.
inline std::string user_data_dir = "system";
