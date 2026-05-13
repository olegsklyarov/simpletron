#include <stdio.h>

struct SIMULATOR {
    // MEMORY
    int memory[100];

    // REGISTERS
    int accumulator;
    int instructionCounter; // aka IP - instruction pointer
    
    int instructionRegister; // copy of the currently executed instruction
    char operationCode;
    char operand;
};

char sign(int value) {
    return value < 0 ? '-' : '+';
}

void dump(struct SIMULATOR s) {
    printf("REGISTERS:\n");
    printf("accumulator           %c%04d\n", sign(s.accumulator), s.accumulator);
    printf("instructionConter        %02d\n", s.instructionCounter);
    printf("instructionRegister   %c%04d\n", sign(s.instructionRegister), s.instructionRegister);
    printf("operationCode            %02d\n", s.operationCode);
    printf("operand                  %02d\n", s.operand);
    
    printf("\n");
    
    printf("MEMORY:\n");

    printf("  ");
    for (int i = 0; i < 10; i++) printf("%6d", i);
    printf("\n");

    for (int y = 0; y < 100; y += 10) {
        printf("%2d", y);
        for (int x = 0; x < 10; x++) {
            int m = s.memory[y + x];
            printf("%2c%04d", sign(m), m);
        }
        printf("\n");
    }
}

int main() {
    printf("*** Welcome to Simpletron! ***\n\n");
    printf("*** Please enter your program one instruction ***\n");
    printf("*** (or data word) at a time. I will type the ***\n");
    printf("*** location number and a question mark (?). ***\n");
    printf("*** You then type the word for that location. ***\n");
    printf("*** Type the sentinel -99999 to stpo entering ***\n");
    printf("*** your program. ***\n\n");


    struct SIMULATOR s = {};

    dump(s);

    // Load SML program into the memory

    return 0;
}
