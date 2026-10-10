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

from diplomacy import Game

class GameExecution:
    _game: Game

    def __init__(self, args: argparse.Namespace):
        round_norm = args.round.strip().lower().replace(" ", "")
        is_initial_round = "spring1901" in round_norm or "s1901" in round_norm
    
        if is_initial_round:
            print("Initializing a brand new game engine state")
            self._game = Game()
            return
    
        if not os.path.exists(args.state):
            print(f"State file {args.state} not found. Required for rounds other than Spring 1901", file=sys.stderr)
            sys.exit(1)
    
        print(f"--> Loading current game state from {args.state}...")
        with open(args.state, 'r') as f:
            try:
                state_data = json.load(f)
                self._game = Game(state=state_data)
            except Exception as e:
                print(f"Error parsing game state JSON: {e}", file=sys.stderr)
                sys.exit(1)

    def get_game_phase(self) -> str:
        return self._game.phase

    def adjudicate(self) -> None:
        print("--> Resolving unit matrix mechanics...")
        self._game.process()

    def issue_orders(self, submitted_orders: json, initial_engine_phase: str) -> dict:
        print(f"--> Staging orders for game phase: {initial_engine_phase}...")
        print(f"Current Engine Phase is {self._game.phase}")

        for country, orders in submitted_orders.items():
            country_upper = country.upper()
            if country_upper in self._game.powers:
                sanitized_orders = []
                for order in orders:
                    clean_order = order.strip()
                    sanitized_orders.append(clean_order)
                self._game.set_orders(country_upper, sanitized_orders)
            else:
                print(f"Warning: Power '{country}' is unrecognized by the engine setup", file=sys.stderr)

        registered_orders = {country: self._game.get_orders(country) for country in self._game.powers.keys()}
        
        return registered_orders

    def export_json_board(self, args: argparse.Namespace) -> None:
        with open(args.out_state, 'w') as f:
            json.dump(self._game.to_dict(), f, indent=4)
        print(f"Successfully wrote new game state to: {args.out_state}")

    def generate_report(self, args: argparse.Namespace, initial_engine_phase: str, registered_orders: json) -> None:
        md_report = []
        md_report.append("# Diplomacy Round Adjudication Report")
        md_report.append(f"**Processed Round:** {args.round} (*engine signature: {initial_engine_phase}*)")
        md_report.append(f"**Next Game Phase:** {self._game.phase}\n")
        md_report.append("---")
        md_report.append("## Turn Results")

        order_outcomes = self._game.get_order_status()

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
                    emoji = self._get_emoji(outcome_str)
                    md_report.append(f"- {emoji} `{user_friendly_order}` **->** `{outcome_str.upper()}`")

            md_report.append("")

        md_report.append("---")
        md_report.append("*Report automatically generated via DATC compliant engine matrices*")

        with open(args.out_report, 'w', encoding='utf-8') as f:
            f.write("\n".join(md_report))
        print(f"Successfully saved Markdown report to {args.out_report}")

    @staticmethod
    def _get_emoji(outcome: str) -> str:
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


def main():
    parser = argparse.ArgumentParser(
        description="Adjudicate a single round of a diplomacy mail game via CLI arguments"
    )

    add_arguments(parser)

    args = parser.parse_args()

    game = GameExecution(args)

    submitted_orders = read_orders(args)
    initial_engine_phase = game.get_game_phase()

    registered_orders = game.issue_orders(submitted_orders, initial_engine_phase)
    game.adjudicate()
    game.export_json_board(args)
    game.generate_report(args, initial_engine_phase, registered_orders)

def add_arguments(parser: argparse.ArgumentParser) -> None:
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


if __name__ == '__main__':
    main()
