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
  typedef struct {
    int i;
    int j;
  } Cell;

  size_t n = (size_t)N;
  size_t capacity = n * n;

  unsigned char *active = calloc(capacity, sizeof(unsigned char));
  unsigned char *queued = calloc(capacity, sizeof(unsigned char));
  Cell *queue = malloc(capacity * sizeof(*queue));

  if (!active || !queued || !queue)
    die("malloc failed for stabilization");

  size_t head = 0;
  size_t tail = 0;
  size_t count = 0;

  int64_t center = N / 2;
  int64_t radius_squared = center * center;

  for (int i = 0; i < N; ++i) {
    for (int j = 0; j <= MAX(i, N - 1 - i); ++j) {
      int64_t di = (int64_t)i - center;
      int64_t dj = (int64_t)j - center;

      if (di * di + dj * dj > radius_squared)
        continue;

      size_t id = (size_t)i * n + (size_t)j;
      active[id] = 1;

      if (grid[i][j] >= 4) {
        queue[tail] = (Cell){i, j};
        if (++tail == capacity)
          tail = 0;
        ++count;
        queued[id] = 1;
      }
    }
  }

  //Process the node in the queue until it is empty
  while (count > 0) {
    Cell cell = queue[head];
    if (++head == capacity)
      head = 0;
    --count;
    int i = cell.i;
    int j = cell.j;
    size_t id = (size_t)i * n + (size_t)j;
    queued[id] = 0;

    // 一次执行当前格子所有可以合法进行的坍塌
    int q = grid[i][j] / 4;
    grid[i][j] %= 4;

    // 收集数组范围内的四个邻居
    Cell neighbors[4];
    int neighbor_count = 0;

    if (i > 0)
      neighbors[neighbor_count++] = (Cell){i - 1, j};
    if (j > 0)
      neighbors[neighbor_count++] = (Cell){i, j - 1};
    if (i < N - 1)
      neighbors[neighbor_count++] = (Cell){i + 1, j};
    if (j < N - 1)
      neighbors[neighbor_count++] = (Cell){i, j + 1};

    for (int k = 0; k < neighbor_count; ++k) {
      int ni = neighbors[k].i;
      int nj = neighbors[k].j;
      size_t neighbor = (size_t)ni * n + (size_t)nj;

      grid[ni][nj] += q;

      if (active[neighbor] &&
          grid[ni][nj] >= 4 &&
          !queued[neighbor]) {
        queue[tail] = neighbors[k];
        if (++tail == capacity)
          tail = 0;
        ++count;
        queued[neighbor] = 1;
      }
    }
  }

  free(queue);
  free(queued);
  free(active);
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
