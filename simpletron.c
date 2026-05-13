#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>

#define MEMORY_SIZE 100
#define WORD_MIN (-9999)
#define WORD_MAX 9999
#define WORD_SPAN ((WORD_MAX) - (WORD_MIN) + 1)
#define PROGRAM_END_SENTINEL (-99999)

#define OPERATION_READ 10
#define OPERATION_WRITE 11
#define OPERATION_LOAD 20
#define OPERATION_STORE 21
#define OPERATION_ADD 30
#define OPERATION_SUBTRACT 31
#define OPERATION_DIVIDE 32
#define OPERATION_MULTIPLY 33
#define OPERATION_BRANCH 40
#define OPERATION_BRANCH_NEG 41
#define OPERATION_BRANCH_ZERO 42
#define OPERATION_HALT 43

typedef struct simpletron
{
    int memory[MEMORY_SIZE];
    int accumulator;
    int instructionCounter;
    int instructionRegister;
} simpletron_t;

typedef enum word_input_status
{
    WORD_INPUT_OK,
    WORD_INPUT_ERR_STDIN,
    WORD_INPUT_ERR_OUT_OF_RANGE,
    WORD_INPUT_ERR_NO_DATA,
    WORD_INPUT_ERR_TRAILING_DATA,
    WORD_INPUT_ERR_LINE_TOO_LONG,
} word_input_status_t;

typedef struct word_input_result
{
    word_input_status_t status;
    int value;
} word_input_result_t;

static int wrap_accumulator_wide(long long acc)
{
    long long span = WORD_SPAN;
    long long x = acc;
    x = (x - WORD_MIN) % span;
    if (x < 0)
    {
        x += span;
    }
    return (int)(x + WORD_MIN);
}

static void dump(const simpletron_t *s)
{
    fprintf(stderr, "REGISTERS:\n");
    fprintf(stderr, "accumulator           %+05d\n", s->accumulator);
    fprintf(stderr, "instructionCounter       %02d\n", s->instructionCounter);
    fprintf(stderr, "instructionRegister   %+05d\n", s->instructionRegister);

    fprintf(stderr, "\n");

    fprintf(stderr, "MEMORY:\n");

    fprintf(stderr, "  ");
    for (int i = 0; i < 10; i++)
    {
        fprintf(stderr, "%6d", i);
    }
    fprintf(stderr, "\n");

    for (int y = 0; y < MEMORY_SIZE; y += 10)
    {
        fprintf(stderr, "%2d", y);
        for (int x = 0; x < 10; x++)
        {
            fprintf(stderr, " %+05d", s->memory[y + x]);
        }
        fprintf(stderr, "\n");
    }
}

static word_input_result_t word_input(FILE *f)
{
    enum
    {
        BUF_SIZE = 256
    };
    char buffer[BUF_SIZE];

    if (fgets(buffer, sizeof(buffer), f) == NULL)
    {
        fprintf(stderr, "word input failed\n");
        word_input_result_t r = {WORD_INPUT_ERR_STDIN, 0};
        return r;
    }

    if (strchr(buffer, '\n') == NULL && !feof(f))
    {
        int c;
        while ((c = fgetc(f)) != '\n' && c != EOF)
        {
        }
        word_input_result_t r = {WORD_INPUT_ERR_LINE_TOO_LONG, 0};
        return r;
    }

    char *endptr;
    errno = 0;
    long value = strtol(buffer, &endptr, 10);
    if (errno == ERANGE && (value == LONG_MAX || value == LONG_MIN))
    {
        word_input_result_t r = {WORD_INPUT_ERR_OUT_OF_RANGE, 0};
        return r;
    }

    if (endptr == buffer)
    {
        word_input_result_t r = {WORD_INPUT_ERR_NO_DATA, 0};
        return r;
    }

    while (*endptr == ' ' || *endptr == '\t')
    {
        endptr++;
    }
    if (*endptr == '\r')
    {
        endptr++;
    }
    if (*endptr != '\n' && *endptr != '\0')
    {
        word_input_result_t r = {WORD_INPUT_ERR_TRAILING_DATA, 0};
        return r;
    }

    if (value == PROGRAM_END_SENTINEL || (WORD_MIN <= value && value <= WORD_MAX))
    {
        word_input_result_t r = {WORD_INPUT_OK, (int)value};
        return r;
    }

    word_input_result_t r = {WORD_INPUT_ERR_OUT_OF_RANGE, 0};
    return r;
}

static int run(simpletron_t *s)
{
    for (; s->instructionCounter < MEMORY_SIZE; s->instructionCounter++)
    {
        s->instructionRegister = s->memory[s->instructionCounter];
        int operationCode = s->instructionRegister / 100;
        int operand = s->instructionRegister % 100;

        if (operationCode == OPERATION_READ)
        {
            word_input_result_t wr = word_input(stdin);
            if (wr.status != WORD_INPUT_OK)
            {
                fprintf(stderr, "[%d] Error reading word, status: %d\n",
                        s->instructionCounter, (int)wr.status);
                dump(s);
                return EXIT_FAILURE;
            }
            s->memory[operand] = wr.value;
        }
        else if (operationCode == OPERATION_WRITE)
        {
            printf("%d\n", s->memory[operand]);
        }
        else if (operationCode == OPERATION_LOAD)
        {
            s->accumulator = s->memory[operand];
        }
        else if (operationCode == OPERATION_STORE)
        {
            s->memory[operand] = s->accumulator;
        }
        else if (operationCode == OPERATION_ADD)
        {
            long long sum = (long long)s->accumulator + (long long)s->memory[operand];
            s->accumulator = wrap_accumulator_wide(sum);
        }
        else if (operationCode == OPERATION_SUBTRACT)
        {
            long long diff = (long long)s->accumulator - (long long)s->memory[operand];
            s->accumulator = wrap_accumulator_wide(diff);
        }
        else if (operationCode == OPERATION_DIVIDE)
        {
            int divisor = s->memory[operand];
            if (divisor == 0)
            {
                fprintf(stderr, "Attempt to divide by zero\n");
                dump(s);
                return EXIT_FAILURE;
            }
            s->accumulator /= divisor;
        }
        else if (operationCode == OPERATION_MULTIPLY)
        {
            long long prod = (long long)s->accumulator * (long long)s->memory[operand];
            s->accumulator = wrap_accumulator_wide(prod);
        }
        else if (operationCode == OPERATION_BRANCH)
        {
            s->instructionCounter = operand - 1;
        }
        else if (operationCode == OPERATION_BRANCH_NEG)
        {
            if (s->accumulator < 0)
            {
                s->instructionCounter = operand - 1;
            }
        }
        else if (operationCode == OPERATION_BRANCH_ZERO)
        {
            if (s->accumulator == 0)
            {
                s->instructionCounter = operand - 1;
            }
        }
        else if (operationCode == OPERATION_HALT)
        {
            return EXIT_SUCCESS;
        }
        else
        {
            fprintf(stderr, "[%d] Error: unknown operation code: %d\n",
                    s->instructionCounter, operationCode);
            dump(s);
            return EXIT_FAILURE;
        }
    }
    fprintf(stderr, "Instruction counter out of range\n");
    dump(s);
    return EXIT_FAILURE;
}

int main(int argc, char **argv)
{
    if (argc != 2)
    {
        fprintf(stderr, "Usage: ./simpletron src.txt\n");
        return EXIT_FAILURE;
    }
    FILE *f = fopen(argv[1], "r");
    if (f == NULL)
    {
        fprintf(stderr, "Failed to open file %s\n", argv[1]);
        return EXIT_FAILURE;
    }

    simpletron_t s = {0};
    int load_ok = 1;

    for (int counter = 0;; counter++)
    {
        word_input_result_t wr = word_input(f);
        if (wr.status != WORD_INPUT_OK)
        {
            fprintf(stderr, "invalid word, status: %d\n", (int)wr.status);
            load_ok = 0;
            break;
        }
        if (wr.value == PROGRAM_END_SENTINEL)
        {
            break;
        }
        if (counter >= MEMORY_SIZE)
        {
            fprintf(stderr, "Too many words in program\n");
            load_ok = 0;
            break;
        }
        s.memory[counter] = wr.value;
    }

    fclose(f);

    if (!load_ok)
    {
        dump(&s);
        return EXIT_FAILURE;
    }

    return run(&s);
}
