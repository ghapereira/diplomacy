"""
Example input file

{
    "FRANCE": [
        "A PAR - BUR",
        "F BRE - MAO",
        "A MAR S A PAR - BUR"
    ],
    "ENGLAND": [
        "F LON - NTH",
        "A LIV - EDI",
        "F EDI C A LIV - NTH"
    ]
}

"""

import argparse
import json
import os
import sys

try:
    from diplomacy import Game
except ImportError:
    print('Error: the "diplomacy" package is not installed', file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Adjudicate a single round of a diplomacy mail game via CLI arguments"
    )
    parser.add_argument(
        '--round',
        required=True,
        help='The current game round name (e.g. "Spring 1901", "S1901M", "Fall 1902")'
    )

    parser.add_argument(
        '--orders',
        required=True,
        help="Path to the JSON file containing the players' text orders"
    )

    parser.add_argument(
        '--state',
        help="Path to the JSON file containing the game current state"
    )

    parser.add_argument(
        '--out-state',
        default='next_game_state.json',
        help="Output destination path for the updated state JSON file"
    )

    parser.add_argument(
        '--out-report',
        default='round_report.md',
        help="Path to the Markdown round summary ledger"
    )

    args = parser.parse_args()

    game = init_round(args)
    submitted_orders = read_orders(args)

    initial_engine_phase = game.phase

    registered_orders = issue_orders(submitted_orders, game, initial_engine_phase)

    adjudication(game)
    export_json_board(args, game)
    generate_report(args, game, initial_engine_phase, registered_orders)

def init_round(args: argparse.Namespace) -> Game:
    round_norm = args.round.strip().lower().replace(" ", "")
    is_initial_round = "spring1901" in round_norm or "s1901" in round_norm

    if is_initial_round:
        print("Initializing a brand new game engine state")
        game = Game()
        return game

    if not os.path.exists(args.state):
        print(f"State file {args.state} not found. Required for rounds other than Spring 1901", file=sys.stderr)
        sys.exit(1)

    print(f"--> Loading current game state from {args.state}...")
    with open(args.state, 'r') as f:
        try:
            state_data = json.load(f)
            game = Game(state=state_data)
        except Exception as e:
            print(f"Error parsing game state JSON: {e}", file=sys.stderr)
            sys.exit(1)

    return game

def read_orders(args: argparse.Namespace) -> json:
    if not os.path.exists(args.orders):
        print(f"Error: orders file {args.orders} not found", file=sys.stderr)
        sys.exit(1)
    with open(args.orders, 'r') as f:
        try:
            submitted_orders = json.load(f)
        except Exception as e:
            print(f"Error parsing game orders JSON: {e}", file=sys.stderr)
            sys.exit(1)
        return submitted_orders

def issue_orders(submitted_orders: json, game: Game, initial_engine_phase: str) -> dict:
    print(f"--> Staging orders for game phase: {initial_engine_phase}...")
    print(f"Current Engine Phase is {game.phase}")

    for country, orders in submitted_orders.items():
        country_upper = country.upper()
        if country_upper in game.powers:
            sanitized_orders = []
            for order in orders:
                clean_order = order.strip()
                sanitized_orders.append(clean_order)
            game.set_orders(country_upper, sanitized_orders)
        else:
            print(f"Warning: Power '{country}' is unrecognized by the engine setup", file=sys.stderr)

    registered_orders = {country: game.get_orders(country) for country in game.powers.keys()}
    
    return registered_orders

def adjudication(game: Game) -> None:
    print("--> Resolving unit matrix mechanics...")
    game.process()

def export_json_board(args: argparse.Namespace, game: Game) -> None:
    with open(args.out_state, 'w') as f:
        json.dump(game.to_dict(), f, indent=4)
    print(f"Successfully wrote new game state to: {args.out_state}")

def generate_report(args: argparse.Namespace, game: Game, initial_engine_phase: str, registered_orders: json) -> None:
    md_report = []
    md_report.append("# Diplomacy Round Adjudication Report")
    md_report.append(f"**Processed Round:** {args.round} (*engine signature: {initial_engine_phase}*)")
    md_report.append(f"**Next Game Phase:** {game.phase}\n")
    md_report.append("---")
    md_report.append("## Turn Results")

    order_outcomes = game.get_order_status()

    for country in sorted(registered_orders):
        md_report.append(f"### {country}")
        engine_orders = registered_orders[country]

        if not engine_orders:
            md_report.append("*No orders received (units hold).*")
        else:
            for canonical_order in engine_orders:
                outcome = order_outcomes.get(canonical_order, ["Resolved"])
                outcome_str = ", ".join(outcome) if isinstance(outcome, list) else str(outcome)
                user_friendly_order = canonical_order.replace(" M ", " - ")
                emoji = get_emoji(outcome_str)
                md_report.append(f"- {emoji} `{user_friendly_order}` **->** `{outcome_str.upper()}`")

        md_report.append("")

    md_report.append("---")
    md_report.append("*Report automatically generated via DATC compliant engine matrices*")

    with open(args.out_report, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_report))
    print(f"Successfully saved Markdown report to {args.out_report}")

def get_emoji(outcome: str) -> str:
    outcome_str = outcome.lower()
    if "success" in outcome_str or "resolved" in outcome_str:
        return "V"
    if "bounce" in outcome_str or "fail" in outcome_str:
        return "X"
    if "cut" in outcome_str or "disrupted" in outcome_str:
        return "K"
    if "void" in outcome_str:
        return "W"
    return " "


if __name__ == '__main__':
    main()
