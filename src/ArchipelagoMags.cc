// Archipelago mag feeding: "simple" mode replaces all 8 of BB's mag feed tables with one flat table, so every mag form
// gains the same amount per item from level 0 to 200 (vanilla tables get stingier as the mag evolves). Feed results
// are computed by both the server (apply_mag_feed_result) and the client, from the same ItemPMT: BB clients download it
// from the server at login (the BB stream file), so we edit the table and regenerate the stream file. Players already
// logged in keep the old table until they log in again.
// Research: the notes' research/mags.md.
#include <algorithm>
#include <memory>

#include "Archipelago.hh"
#include "DataIndex.hh"
#include "ItemParameterTable.hh"

namespace {

// Stat progress per feeding before the multiplier (100 progress = 1 mag level)
constexpr int SMALL = 40;
constexpr int MEDIUM = 60;
constexpr int LARGE = 80;
// Every item also raises IQ and synchro a little (they drive the mag's triggered effects), like the base mag's table;
// the atomizers raise only these, so they don't disturb a stat the player is building
constexpr int ITEM_IQ_SYNCHRO = 3;
constexpr int ATOMIZER_IQ_SYNCHRO = 10;
// The client stores each feed result as int8
constexpr int MAX_FEED_RESULT = 127;

struct SimpleFeedResult {
  int def, pow, dex, mind, iq, synchro;
};

// Order matches the item index in apply_mag_feed_result (Items.cc): mates, fluids, Antidote, Antiparalysis, atomizers
constexpr SimpleFeedResult SIMPLE_TABLE[11] = {
    // DEF, POW, DEX, MIND, IQ, synchro
    {0, SMALL, 0, 0, ITEM_IQ_SYNCHRO, ITEM_IQ_SYNCHRO}, // Monomate
    {0, MEDIUM, 0, 0, ITEM_IQ_SYNCHRO, ITEM_IQ_SYNCHRO}, // Dimate
    {0, LARGE, 0, 0, ITEM_IQ_SYNCHRO, ITEM_IQ_SYNCHRO}, // Trimate
    {0, 0, 0, SMALL, ITEM_IQ_SYNCHRO, ITEM_IQ_SYNCHRO}, // Monofluid
    {0, 0, 0, MEDIUM, ITEM_IQ_SYNCHRO, ITEM_IQ_SYNCHRO}, // Difluid
    {0, 0, 0, LARGE, ITEM_IQ_SYNCHRO, ITEM_IQ_SYNCHRO}, // Trifluid
    {0, 0, SMALL, 0, ITEM_IQ_SYNCHRO, ITEM_IQ_SYNCHRO}, // Antidote
    // No vanilla item is mainly DEF; Antiparalysis (mostly DEX in vanilla) is the closest, in one mid-stage table
    {SMALL, 0, 0, 0, ITEM_IQ_SYNCHRO, ITEM_IQ_SYNCHRO}, // Antiparalysis
    {0, 0, 0, 0, ATOMIZER_IQ_SYNCHRO, 0}, // Sol Atomizer
    {0, 0, 0, 0, 0, ATOMIZER_IQ_SYNCHRO}, // Moon Atomizer
    {0, 0, 0, 0, ATOMIZER_IQ_SYNCHRO, ATOMIZER_IQ_SYNCHRO}, // Star Atomizer
};

phosg::JSON simple_feed_tables_json() {
  auto scaled = [](int stat) { return std::min(stat * ap_mag_feed_multiplier, MAX_FEED_RESULT); };
  auto table = phosg::JSON::list();
  for (const auto& r : SIMPLE_TABLE) {
    ItemParameterTable::MagFeedResult result;
    result.def = scaled(r.def);
    result.pow = scaled(r.pow);
    result.dex = scaled(r.dex);
    result.mind = scaled(r.mind);
    result.iq = r.iq;
    result.synchro = r.synchro;
    table.emplace_back(result.json());
  }
  auto tables = phosg::JSON::list();
  for (size_t z = 0; z < 8; z++) { // every mag form uses the same table, whichever index it names
    tables.emplace_back(phosg::JSON(table));
  }
  return tables;
}

} // namespace

void ap_apply_mag_feeding(DataIndex& data) {
  // Keep the loaded table to restore or rebuild from. If the slot no longer holds the table we made, it was (re)loaded
  // since, so that's the new vanilla.
  static std::shared_ptr<const ItemParameterTable> vanilla, generated;
  auto& slot = data.item_parameter_tables.at(static_cast<size_t>(Version::BB_V4));
  if (!generated || (slot != generated)) {
    vanilla = slot;
  }

  if (ap_simple_mag_feeding) {
    auto json = vanilla->json();
    json.at("MagFeedResults") = simple_feed_tables_json();
    generated = ItemParameterTable::from_json(json);
    slot = generated;
  } else {
    generated = vanilla;
    slot = vanilla;
  }
  data.generate_bb_stream_file();
}
