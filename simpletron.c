#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>

struct SIMULATOR
{
    int memory[100];

    // REGISTERS
    int accumulator;
    int instructionCounter;  // aka IP - instruction pointer
    int instructionRegister; // copy of the currently executed instruction
    char operationCode;
    char operand;
};

void dump(struct SIMULATOR s)
{
    printf("REGISTERS:\n");
    printf("accumulator           %+05d\n", s.accumulator);
    printf("instructionConter        %02d\n", s.instructionCounter);
    printf("instructionRegister   %+05d\n", s.instructionRegister);
    printf("operationCode            %02d\n", s.operationCode);
    printf("operand                  %02d\n", s.operand);

    printf("\n");

    printf("MEMORY:\n");

    printf("  ");
    for (int i = 0; i < 10; i++)
        printf("%6d", i);
    printf("\n");

    for (int y = 0; y < 100; y += 10)
    {
        printf("%2d", y);
        for (int x = 0; x < 10; x++)
            printf(" %+05d", s.memory[y + x]);
        printf("\n");
    }
}

const int ERROR_INPUT_STDIN = -100000;
const int ERROR_INPUT_OUT_OF_RANGE = -100001;
const int ERROR_INPUT_NO_DATA = -100002;
const int ERROR_INPUT_TRAILING_DATA = -100003;

int is_error_word(int word)
{
    return word <= ERROR_INPUT_STDIN;
}

int word_input()
{
    char buffer[10];

    if (fgets(buffer, sizeof(buffer), stdin) == NULL)
    {
        printf("\nword input failed");
        return ERROR_INPUT_STDIN;
    }

    char *endptr;
    errno = 0;
    long value = strtol(buffer, &endptr, 10);
    if ((errno == ERANGE && (value == LONG_MAX || value == LONG_MIN)))
    {
        return ERROR_INPUT_OUT_OF_RANGE;
    }

    if (endptr == buffer)
    {
        return ERROR_INPUT_NO_DATA;
    }

    if (*endptr != '\n' && *endptr != '\0')
    {
        return ERROR_INPUT_TRAILING_DATA;
    }

    if (value == -99999 || (-9999 <= value && value <= 9999))
    {
        return value;
    }

    return ERROR_INPUT_OUT_OF_RANGE;
}

int main()
{
    printf("*** Welcome to Simpletron! ***\n\n");
    printf("*** Please enter your program one instruction ***\n");
    printf("*** (or data word) at a time. I will type the ***\n");
    printf("*** location number and a question mark (?). ***\n");
    printf("*** You then type the word for that location. ***\n");
    printf("*** Type the sentinel -99999 to stpo entering ***\n");
    printf("*** your program. ***\n\n");

    struct SIMULATOR s = {};

    // Load SML program into the memory
    int inputCounter = 0;
    int word = 0;
    for (;;)
    {
        printf("%02d ? ", inputCounter);
        word = word_input();
        if (is_error_word(word))
        {
            printf("invalid word, error code: %d\n", word);
            continue;
        }
        if (word == -99999)
        {
            break;
        }
        s.memory[inputCounter++] = word;
    }

    dump(s);

    return 0;
}
