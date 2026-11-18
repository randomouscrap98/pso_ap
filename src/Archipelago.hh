#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>

// Archipelago slot settings that upstream newserv has no config for. Server-wide (one newserv per AP slot); set by
// `ap-set` (ArchipelagoShellCommands.cc), runtime only.
inline float ap_money_multiplier = 1.0f;

// Meseta the player receives (enemy/box drops, quest rewards) after the slot's multiplier, capped at max_amount
inline uint32_t ap_scale_meseta(uint32_t amount, uint32_t max_amount) {
  double scaled = std::round(amount * static_cast<double>(ap_money_multiplier));
  return static_cast<uint32_t>(std::min<double>(scaled, max_amount));
}
