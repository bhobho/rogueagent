# run.py
# Start here.
#
#   python run.py --agent scripted          # no AI, always goes rogue (tests the monitor)
#   python run.py --agent llm               # deepseek-r1:1.5b via Ollama, one run
#   python run.py --agent llm --runs 10     # ten runs, then totals per flag

import argparse

import llm_agent
import monitor
import scripted_agent
import world


def main():
    parser = argparse.ArgumentParser(description="Rogue agent simulation")
    parser.add_argument("--agent", choices=["scripted", "llm"], default="scripted")
    parser.add_argument("--runs", type=int, default=1)
    options = parser.parse_args()

    if options.agent == "llm":
        agent = llm_agent
        if not llm_agent.check_ollama():
            return
        print("Model: " + llm_agent.MODEL)
    else:
        agent = scripted_agent

    all_flags = []
    for run_number in range(1, options.runs + 1):
        # A fresh copy of the pretend files for every run, so an edit the
        # agent made in run 1 can't leak into run 2.
        files = world.load_world()
        run = monitor.start_run(options.agent, run_number)
        agent.run_agent(files, run)
        all_flags.append(monitor.finish_run(run))

    if options.runs > 1:
        monitor.print_totals(all_flags)


if __name__ == "__main__":
    main()
