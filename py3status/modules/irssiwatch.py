#! /bin/env python
# -*- coding: utf-8 -*-
"""
Watch irssi messagelog.pl output and display unread message notification.

Supports either local instances or remote irssi via ssh. Requires a file dump 
such as messagelog.pl provides.
Note: messagelog.pl can be found at https://gist.github.com/pydsigner/c94aea8f8de8c23cdc43

Configuration parameters:
    - log_path : either an "ssh://[user@]host/file/path" for remote reads or a 
                 "/file/path" for local reads. Tilde paths are supported for 
                 both.
    - format : - format: define custom display format. See placeholders below
    - cache_timeout : how often we refresh this module in seconds
    - color_bad : color for urgent messages
    - color_degraded : color for non-urgent messages
    - color_good : color for no messages

Format of status string placeholders:
    {unread} - total new messages
    {important} - new messages that either mention you or were PMed to you

@author Daniel Foerster <pydsigner@gmail.com>
@license Apache 2.0
"""

import time
import thread
import subprocess
import sys
import signal


click_events = True


class Py3status(object):
    # available configuration parameters
    log_path = '~/irssimessages'
    format = 'IRC: {unread} new'
    cache_timeout = 5
    color_good = None
    color_degraded = None
    color_bad = None

    def __init__(self):
        self._setup = False

    def kill(self, i3s_output_list, i3s_config):
        self.pipe.terminate()

    def on_click(self, *args):
        with self.lock:
            self._reset()

    def ircwatch(self, i3s_output_list, i3s_config):
        if not self._setup:
            self._do_setup()
        
        with self.lock:
            unread = self.unread
            important = self.important
        
        if unread:
            if important:
                color = self.color_bad or i3s_config['color_bad']
            else:
                color = self.color_degraded or i3s_config['color_degraded']
        else:
            color = self.color_good or i3s_config['color_good']
        
        status = self.format.format(unread=unread, important=important)
        
        response = {
            'cached_until': time.time() + self.cache_timeout,
            'full_text': status,
            'color': color
        }
        return response
    
    def _reset(self):
        self.unread = self.important = 0
    
    def _read_pipe(self):
        for L in self.reader:
            with self.lock:
                flag = L[0]
                if flag == '~':
                    self._reset()
                else:
                    self.unread += 1
                    self.important += (flag in '!@')
    
    def _do_setup(self):
        self._reset()
        
        log_path = self.log_path
        command = []
        if log_path.startswith('ssh://'):
            server, log_path = log_path.lstrip('ssh://').split('/', 1)
            command = ['ssh', server]
        command.append('tail -F %s' % log_path)
        
        self.pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=sys.stderr)
        self.reader = iter(self.pipe.stdout.readline, b"")
        
        self.lock = thread.allocate_lock()
        thread.start_new_thread(self._read_pipe, ())
        
        self._setup = True
            

if __name__ == "__main__":
    x = Py3status()
    config = {
        'color_bad': '#FF0000',
        'color_degraded': '#FFFF00',
        'color_good': '#00FF00'
    }
    while True:
        print(x.ircwatch([], config))
        time.sleep(1)
