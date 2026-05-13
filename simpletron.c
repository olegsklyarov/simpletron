#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <limits.h>

struct SIMPLETRON
{
    int memory[100];

    // REGISTERS
    int accumulator;
    int instructionCounter;  // aka IP - instruction pointer
    int instructionRegister; // copy of the currently executed instruction
    char operationCode;
    char operand;
};

void dump(struct SIMPLETRON s)
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

const int OPERATION_READ = 10;
const int OPERATION_WRITE = 11;
const int OPERATION_LOAD = 20;
const int OPERATION_STORE = 21;
const int OPERATOIN_ADD = 30;
const int OPERATION_SUBTRACT = 31;
const int OPERATION_DIVIDE = 32;
const int OPERATION_MULTIPLY = 33;
const int OPERATION_BRANCH = 40;
const int OPERATION_BRANCH_NEG = 41;
const int OPERATION_BRANCH_ZERO = 42;
const int OPERATION_HALT = 43;

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

int run(struct SIMPLETRON s)
{
    for (; s.instructionCounter < 100; s.instructionCounter++)
    {
        s.instructionRegister = s.memory[s.instructionCounter];
        s.operationCode = s.instructionRegister / 100;
        s.operand = s.instructionRegister % 100;

        if (s.operationCode == OPERATION_READ)
        {

            int word = word_input();
            if (is_error_word(word))
            {
                printf("[%d] Error reading word, error code: %d\n", s.instructionCounter, word);
                return -1;
            }
            s.memory[s.operand] = word;
        }
        else if (s.operationCode == OPERATION_WRITE)
        {
            printf("%+05d\n", s.memory[s.operand]);
        }
        else if (s.operationCode == OPERATION_LOAD)
        {
            s.accumulator = s.memory[s.operand];
        }
        else if (s.operationCode == OPERATION_STORE)
        {
            s.memory[s.operand] = s.accumulator;
        }
        else if (s.operationCode == OPERATOIN_ADD)
        {
            s.accumulator += s.memory[s.operand];
        }
        // else if (s.operationCode == OPERATION_SUBTRACT) {
        //     s.accumulator -= s.memory[s.operand];
        // }
        else if (s.operationCode == OPERATION_HALT)
        {
            printf("*** Simpletron execution terminated ***\n");
            return 0;
        }
        else
        {
            printf("[%d] Error: unknown operation code: %d\n", s.instructionCounter, s.operationCode);
            return -1;
        }
    }
    return -1000;
}

int main()
{
    printf("*** Welcome to Simpletron! ***\n");
    printf("\n");
    printf("*** Please enter your program one instruction ***\n");
    printf("*** (or data word) at a time. I will type the ***\n");
    printf("*** location number and a question mark (?).  ***\n");
    printf("*** You then type the word for that location. ***\n");
    printf("*** Type the sentinel -99999 to stpo entering ***\n");
    printf("*** your program. ***\n");
    printf("\n");

    struct SIMPLETRON s = {};

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

    printf("\n");
    printf("*** Program loading completed ***\n");
    printf("*** Program execution begins  ***\n");
    printf("\n");

    run(s);

    // dump(s);

    return 0;
}
