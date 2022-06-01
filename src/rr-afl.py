import sys
import subprocess as sp
import re
import os
import time

if __name__ == "__main__":
    switching_minutes_budget = 61
    fuzz_run_floor = 10
    rounds = 2

    env_re = re.compile('(\S+)=(\S+)')
    sub_re = re.compile('\@@@(\d+)')
    in_re = re.compile('-i\s+(\S+)')
    out_re = re.compile('-o\s+(\S+)')

    cmdfile = sys.argv[1]
    scratchdir = "scratch"
    sp.run(f"mkdir -p {scratchdir}", shell=True)
    seeds = []
    afl_outs = []
    cu_out = "cu_out"

    with open(cmdfile, "r") as f:
        cmds = f.readlines()

    iter_groups = []

    for (i, cmd) in enumerate(cmds):
        in_match = in_re.search(cmd)
        out_match = out_re.search(cmd)
        afl_outs.append(out_match.group(1))
        seeds.append(f"{scratchdir}/{in_match.group(1)}")
        cmd = cmd.replace(in_match.group(0), f"-i {scratchdir}/{in_match.group(1)}")
        sp.run(f"cp -r {in_match.group(1)} {scratchdir}/{in_match.group(1)}", shell=True)

        iter_groups.append((cmd, seeds, afl_outs))

    
    for r in range(rounds):
        for (i, (cmd, seeds, afl_outs)) in enumerate(iter_groups):
            sub_match = sub_re.search(cmd)
            if sub_match is not None:
                aux_file_prov = sub_match.group(1)
                aux_dir = f"{cu_out}/{aux_file_prov}/queue"
                if os.path.exists(aux_dir) and len(os.listdir(aux_dir)) > 0:
                    aux_files = os.listdir(aux_dir)
                else:
                    aux_files = os.listdir(seeds[int(aux_file_prov)])
                sub_commands = [cmd.replace(f"@@@{aux_file_prov}", f"{os.getcwd()}/{af}") for af in aux_files]
                timeout_mins = int(max(switching_minutes_budget / len(sub_commands), fuzz_run_floor))
            else:
                sub_commands = [cmd]
                timeout_mins = switching_minutes_budget


            for j, sc in enumerate(sub_commands):
                matches = env_re.findall(sc)
                sp.run(f"cp -r {cu_out}/{i}/queue/* {seeds[i]}/{i}", shell=True)
                try:
                    sp.run(sc, env=dict(matches), timeout=timeout_mins, shell=True)
                except sp.TimeoutExpired:
                    sp.run("pkill afl", shell=True)  # @TODO HACK

                sp.run(f"mkdir -p {cu_out}/{i}/queue", shell=True)
                sp.run(f"mkdir -p {cu_out}/{i}/crashes", shell=True)
                sp.run(f"cp -r {afl_outs[i]}/queue/* {cu_out}/{i}/queue", shell=True)
                sp.run(f"cp -r {afl_outs[i]}/crashes/* {cu_out}/{i}/crashes", shell=True)
                sp.run(f"rm -r {afl_outs[i]}/*", shell=True)
                print(sc)
                print(f"sub command {j} of {len(sub_commands)-1}, group {i} of {len(iter_groups)-1}")
                time.sleep(5)


