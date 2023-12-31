/* -*- Mode: C ; c-basic-offset: 2 -*- */
/* termsize - Adjust rows and cols of /dev/tty
   to match the size of attached terminal (emulator) */
/* SPDX-FileCopyrightText: Copyright © 2023 Nedko Arnaudov */
/* SPDX-License-Identifier: GPL-3 */

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <string.h>
#include <stdio.h>
#include <termios.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <stdbool.h>
#include <stdlib.h>
#include <limits.h>
#include <errno.h>

int fd;
char buf[256];

struct curpos
{
  int row;
  int col;
};

void write_asciiz(const char * str)
{
  ssize_t sret;
  size_t len;

  len = strlen(str);
loop:
  sret = write(fd, str, len);
  if (sret == -1) abort();
  str += (size_t)sret;
  len -= (size_t)sret;
  if (len > 0) goto loop;
}

void get_cursor_position(struct curpos * pos)
{
  int i;
  char * p;
  ssize_t sret;

  write_asciiz("\033[6n");

  i = 0;
loop:
  if (i == sizeof(buf)) abort();

  sret = read(fd, buf + i, 1);
  if (sret == -1)
  {
    if (errno == EINTR) goto loop;
    abort();
  }
  if (sret == 0) goto loop;
  if (sret != 1) abort();

  if (buf[i] == 'R')
  {
    buf[i] = 0;
    if (buf[0] != '\e' || buf[1] != '[') abort();
    p = strchr(buf + 2, ';');
    if (p == NULL) abort();
    *p++ = 0;
    pos->row = atoi(buf + 2);
    pos->col = atoi(p);
    if (pos->row == 0 || pos->col == 0) abort();
    return;
  }

  i++;
  goto loop;
}


void set_cursor_position(const struct curpos * pos)
{
  sprintf(buf, "\033[%d;%dH", pos->row, pos->col);
  write_asciiz(buf);
}

void get_terminal_size(struct curpos * size)
{
  struct curpos oldpos;

  get_cursor_position(&oldpos);

  // TIOCSWINSZ cannot set sizes more than USHRT_MAX anyway
  size->row = size->col = USHRT_MAX;
  set_cursor_position(size);
  get_cursor_position(size);

  set_cursor_position(&oldpos);
}

int main(void)
{
  struct termios tty_save;
  struct termios tty;
  struct curpos size;
  struct winsize winsize;

  fd = open("/dev/tty", O_RDWR);

  tcgetattr(fd, &tty_save);
  tty = tty_save;
  tty.c_lflag &= ~(ICANON|ECHO);
  tcsetattr(fd, TCSANOW, &tty);

  get_terminal_size(&size);
  tcsetattr(fd, TCSANOW, &tty_save);

  printf("%d rows, %d cols\n", size.row, size.col);

  winsize.ws_row = (unsigned short)size.row;
  winsize.ws_col = (unsigned short)size.col;
  ioctl(fd, TIOCSWINSZ, &winsize);
}
