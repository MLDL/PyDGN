import os
import sys
import time
import tqdm
import datetime
import threading


def clear_screen():
    try:
        os.system('clear')
    except Exception as e:
        try:
            os.system('cls')
        except Exception:
            pass


class ProgressManager:

    '''
    Possible vars of bar_format:
          l_bar, bar, r_bar,
          n, n_fmt, total, total_fmt,
          percentage, elapsed, elapsed_s,
          ncols, nrows, desc, unit,
          rate, rate_fmt, rate_noinv,
          rate_noinv_fmt, rate_inv, rate_inv_fmt,
          postfix, unit_divisor, remaining, remaining_s
    '''

    def _init_selection_pbar(self, i, j):
        position = i*self.inner_folds + j
        pbar = tqdm.tqdm(total=self.no_configs, ncols=self.ncols, ascii=True,
                         position=position, unit="config",
                         bar_format=' {desc} {percentage:3.0f}%|{bar}|{n_fmt}/{total_fmt}{postfix}')
        pbar.set_description(f'Out_{i+1}/Inn_{j+1}')
        mean = str(datetime.timedelta(seconds=0))
        pbar.set_postfix_str(f'(1 cfg every {mean})')
        return pbar

    def _init_assessment_pbar(self, i):
        position = self.outer_folds*self.inner_folds + i
        pbar = tqdm.tqdm(total=self.final_runs, ncols=self.ncols, ascii=True,
                         position=position, unit="config",
                         bar_format=' {desc} {percentage:3.0f}%|{bar}|{n_fmt}/{total_fmt}{postfix}')
        pbar.set_description(f'Final run {i+1}')
        mean = str(datetime.timedelta(seconds=0))
        pbar.set_postfix_str(f'(1 run every {mean})')
        return pbar


    def __init__(self, outer_folds, inner_folds, no_configs, final_runs, show=True):
        self.ncols = 100
        self.outer_folds = outer_folds
        self.inner_folds = inner_folds
        self.no_configs = no_configs
        self.final_runs = final_runs
        self.pbars = []
        self.show = show

        if not self.show:
            return

        clear_screen()
        self.show_header()
        for i in range(self.outer_folds):
            for j in range(self.inner_folds):
                self.pbars.append(self._init_selection_pbar(i, j))

        for i in range(self.outer_folds):
            self.pbars.append(self._init_assessment_pbar(i))

        self.show_footer()

        self.times = [{} for _ in range(len(self.pbars))]

        def refresh_timer():
            threading.Timer(60.0, refresh_timer).start()
            self.refresh()

        refresh_timer()

    def show_header(self):
        '''
        \033[F --> move cursor to the beginning of the previous line
        \033[A --> move cursor up one line
        \033[<N>A --> move cursor up N lines
        '''
        print(f'\033[F\033[A{"*"*((self.ncols-21)//2 + 1)} Experiment Progress {"*"*((self.ncols-21)//2)}\n')

    def show_footer(self):
        pass  # need to work how how to print after tqdm

    def refresh(self):

        self.show_header()
        for i, pbar in enumerate(self.pbars):

            # When resuming, do not consider completed exp. (delta approx. < 1)
            completion_times = [delta for k, (delta, completed) in self.times[i].items() if completed and delta > 1]

            if len(completion_times) > 0:
                min_seconds = min(completion_times)
                max_seconds = max(completion_times)
                mean_seconds = sum(completion_times)/len(completion_times)
            else:
                min_seconds = 0
                max_seconds = 0
                mean_seconds = 0

            mean_time = str(datetime.timedelta(seconds=mean_seconds)).split('.')[0]
            min_time = str(datetime.timedelta(seconds=min_seconds)).split('.')[0]
            max_time = str(datetime.timedelta(seconds=max_seconds)).split('.')[0]
            pbar.set_postfix_str(f'min:{min_time}|avg:{mean_time}|max:{max_time}')

            pbar.refresh()
        self.show_footer()

    def update_state(self, msg):
        if not self.show:
            return

        try:
            type = msg.get('type')

            if type == 'START_CONFIG':
                outer_fold = msg.get('outer_fold')
                inner_fold = msg.get('inner_fold')
                config_id = msg.get('config_id')
                position = outer_fold*self.inner_folds + inner_fold
                configs_times = self.times[position]
                configs_times[config_id] = (time.time(), False)
            elif type == 'END_CONFIG':
                outer_fold = msg.get('outer_fold')
                inner_fold = msg.get('inner_fold')
                config_id = msg.get('config_id')
                position = outer_fold*self.inner_folds + inner_fold
                configs_times = self.times[position]
                # Compute delta t for a specific config
                configs_times[config_id] = (time.time() - configs_times[config_id][0], True)
                # Update progress bar
                self.pbars[position].update()
                self.refresh()
            elif type == 'START_FINAL_RUN':
                outer_fold = msg.get('outer_fold')
                run_id = msg.get('run_id')
                position = self.outer_folds*self.inner_folds + outer_fold
                configs_times = self.times[position]
                configs_times[run_id] = (time.time(), False)
            elif type == 'END_FINAL_RUN':
                outer_fold = msg.get('outer_fold')
                run_id = msg.get('run_id')
                position = self.outer_folds*self.inner_folds + outer_fold
                configs_times = self.times[position]
                # Compute delta t for a specific config
                configs_times[run_id] = (time.time() - configs_times[run_id][0], True)
                # Update progress bar
                self.pbars[position].update()
                self.refresh()
            else:
                raise Exception(f"Cannot parse type of message {type}, fix this.")

        except Exception as e:
            print(e)
            return

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        for pbar in self.pbars:
            pbar.close()
