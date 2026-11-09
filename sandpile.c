#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

#define MIN(a, b) (((a) < (b)) ? (a) : (b))
#define MAX(a, b) (((a) > (b)) ? (a) : (b))

static void die(const char *s) {
  fprintf(stderr, "%s\n", s);
  exit(1);
}

int N = 801;
int **grid;

// you can also use this function to debug print your sandpile
static void render(char *filename) {
  int chan = 3;
  unsigned char *pixels = (unsigned char *)malloc(N * N * chan * sizeof(char));
  int stride = N * chan;
  if (!pixels)
    die("malloc failed for PNG pixel buffer");
  for (int i = 0; i < N; ++i) {
    for (int j = 0; j < N; ++j) {
      unsigned char r = 0, g = 0, b = 0;
      switch (grid[i][j]) {
      case 0: // obsidian
        r = 15;
        g = 15;
        b = 25;
        break;
      case 1: // electric cyan
        r = 0;
        g = 210;
        b = 255;
        break;
      case 2: // vibrant magenta
        r = 230;
        g = 30;
        b = 130;
        break;
      case 3: // bright gold
        r = 255;
        g = 200;
        b = 0;
        break;
      default: // white
        r = 0;
        g = 0;
        b = 0;
      }

      int pid = (i * N + j) * chan;
      pixels[pid] = r;
      pixels[pid + 1] = g;
      pixels[pid + 2] = b;
    }
  }
  if (stbi_write_png(filename, N, N, chan, pixels, stride)) {
    printf("Successfully saved sandpile identity to: %s\n", filename);
  } else {
    die("Error: stb_image_write failed to save png file\n");
  }
  free(pixels);
}

// static void stabilize() {
//   int changed = 0;
//   do {
//     changed = 0;
//     for (int i = 0; i < N; ++i) {
//       for (int j = 0; j <= MAX(i, N - 1 - i); ++j) {
//         if ((i - N / 2) * (i - N / 2) + (j - N / 2) * (j - N / 2) <=
//             (N / 2) * (N / 2)) {
//           if (grid[i][j] < 4)
//             continue;
//           changed = 1; // topple it
//           grid[i][j] -= 4;
//           if (i > 0)
//             grid[i - 1][j]++;
//           if (j > 0)
//             grid[i][j - 1]++;
//           if (i < N - 1)
//             grid[i + 1][j]++;
//           if (j < N - 1)
//             grid[i][j + 1]++;
//         }
//       }
//     }
//   } while (changed);
// }

static void stabilize(void) {
  // Odd-sized Pacman domains are symmetric about the middle row. Only use
  // this reduction when the input values (including sink cells) also match.
  int mirrored = N % 2 != 0;
  if (mirrored) {
    for (int i = 0; i < N / 2; ++i) {
      if (memcmp(grid[i], grid[N - 1 - i], (size_t)N * sizeof(int)) != 0) {
        mirrored = 0;
        break;
      }
    }
  }
  int last_row = mirrored ? N / 2 : N - 1;

  int *lo = malloc((size_t)N * sizeof(*lo));
  int *hi = malloc((size_t)N * sizeof(*hi));
  if (!lo || !hi)
    die("malloc failed for row bounds");

  // Compute the inclusive Pacman column bounds once per stabilization.
  int64_t center = N / 2;
  int64_t radius_squared = center * center;
  for (int i = 0; i <= last_row; ++i) {
    lo[i] = N;
    hi[i] = -1;
    int64_t di = (int64_t)i - center;
    for (int j = 0; j <= MAX(i, N - 1 - i); ++j) {
      int64_t dj = (int64_t)j - center;
      if (di * di + dj * dj <= radius_squared) {
        if (lo[i] == N)
          lo[i] = j;
        hi[i] = j;
      }
    }
  }

  int changed;
  do {
    changed = 0;
    for (int i = 0; i <= last_row; ++i) {
      // The row immediately above the center represents TWO rows feeding
      // the same center cell. The center itself topples only once.
      int down_factor = mirrored && i + 1 == last_row ? 2 : 1;
      for (int j = lo[i]; j <= hi[i]; ++j) {
        if (grid[i][j] < 4)
          continue;

        changed = 1;
        int q = grid[i][j] / 4;
        grid[i][j] %= 4;

        // Preserve transfers to cells outside Pacman but inside the array.
        if (i > 0)
          grid[i - 1][j] += q;
        if (j > 0)
          grid[i][j - 1] += q;
        if (i < last_row)
          grid[i + 1][j] += down_factor * q;
        if (j < N - 1)
          grid[i][j + 1] += q;
      }
    }
  } while (changed);

  if (mirrored) {
    // Include cells outside Pacman to preserve the complete rendered image.
    for (int i = 0; i < last_row; ++i)
      memcpy(grid[N - 1 - i], grid[i], (size_t)N * sizeof(int));
  }

  free(lo);
  free(hi);
}

void find_identity() {
  for (int i = 0; i < N; ++i) {
    for (int j = 0; j < N; ++j) {
      grid[i][j] = 6;
    }
  }
  stabilize();
  for (int i = 0; i < N; ++i) {
    for (int j = 0; j < N; ++j) {
      grid[i][j] = 6 - grid[i][j];
    }
  }
  stabilize();
}

int main(int argc, char **argv) {
  if (argc < 2 || argc > 2) {
    fprintf(stderr, "Usage: %s N\n", argv[0]);
    return EXIT_FAILURE;
  }
  char *end;
  uintmax_t parsed = strtoumax(argv[1], &end, 10);
  if (errno || argv[1][0] < '0' || argv[1][0] > '9' || *end || !parsed ||
      parsed > INT32_MAX)
    die("grid size must be a positive int");
  N = (int)parsed;

  grid = (int **)malloc(N * sizeof(int *));
  for (int i = 0; i < N; ++i) {
    grid[i] = (int *)malloc(N * sizeof(int));
  }

  find_identity();

  render("identity.png");
  for (int i = 0; i < N; ++i) {
    free(grid[i]);
  }
  free(grid);
  return EXIT_SUCCESS;
}
