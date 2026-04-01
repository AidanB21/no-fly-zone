//#############################################################################
//
// FILE:   empty_driverlib_main.c
//
// TITLE:  Empty Project
//
// Empty Project Example
//
// This example is an empty project setup for Driverlib development.
//
//#############################################################################
//
//
// $Copyright:
// Copyright (C) 2013-2025 Texas Instruments Incorporated - http://www.ti.com/
//
// Redistribution and use in source and binary forms, with or without 
// modification, are permitted provided that the following conditions 
// are met:
// 
//   Redistributions of source code must retain the above copyright 
//   notice, this list of conditions and the following disclaimer.
// 
//   Redistributions in binary form must reproduce the above copyright
//   notice, this list of conditions and the following disclaimer in the 
//   documentation and/or other materials provided with the   
//   distribution.
// 
//   Neither the name of Texas Instruments Incorporated nor the names of
//   its contributors may be used to endorse or promote products derived
//   from this software without specific prior written permission.
// 
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 
// "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT 
// LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
// A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT 
// OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
// SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT 
// LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
// DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
// THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT 
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
// $
//#############################################################################

//
// Included Files
//
#include "driverlib.h"
#include "device.h"
#include "board.h"
#include "c2000ware_libraries.h"

#include "sensorReader.h"

//
//  Function Prototypes
//

#define I2C_BASE       I2CB_BASE
#define I2C_ADDR_TEST  0x76      // any 7-bit address
#define I2C_TIMEOUT    100000UL  // simple software timeout

static bool I2C_writeTestByte();


//
// Main
//
void main(void)
{

    //
    // Initialize device clock and peripherals
    //
    Device_init();

    //
    // Disable pin locks and enable internal pull-ups.
    //
    Device_initGPIO();

    //
    // Initialize PIE and clear PIE registers. Disables CPU interrupts.
    //
    Interrupt_initModule();

    //
    // Initialize the PIE vector table with pointers to the shell Interrupt
    // Service Routines (ISR).
    //
    Interrupt_initVectorTable();

    //
    // PinMux and Peripheral Initialization
    //
    Board_init();

    //
    // C2000Ware Library initialization
    //
    C2000Ware_libraries_init();

    //
    // Enable Global Interrupt (INTM) and real time interrupt (DBGM)
    //
    EINT;
    ERTM;
    
        //////////////////////////
        //// Code Initiations ////
        //////////////////////////
    sensorReadings sampleReadings;






    while(1)
    {

     
        // Take the readings from the ADC I gues
        //sensors_openAirCalibration(&sampleReadings);

        sensors_getData(&sampleReadings);
        sensors_convertData(&sampleReadings);

        //////////////////////////////////////////////////////////////////////////////////////////////
        //                                                                                      //////
        //                                      sensors_logData                                 //////
        //                                                                                      //////
        //! @param sensorData : struct that holds sensor values                                  //////
        //! @param logData : 1 to log for algorithm, 0 to print adc values                       //////
        //! @param sample : 'B' if its just box, 'T' if its a tomatoes      //////
        //! @param eggStatus : 'E' if theres an egg, 'X' if NA                                   //////
        //! @param larvaeStatus : 'L' if theres larvae, 'X' if theres no Larvae                  //////
        //! @param pupaeStatus : 'P' if theres pupae, 'X' if theres no pupae                     //////
        //! @param adultStatus : 'A' if theres an adult, 'X' if theres no adult                  //////
        //! @param sampleAge : int, days the sample has been in the box                          //////
        //                                                                                      //////
        //////////////////////////////////////////////////////////////////////////////////////////////
        sensors_logData(&sampleReadings, 1, 'T', 'X', 'X', 'X', 'X', 2);//prints raw and converted and logs data


        DEVICE_DELAY_US(1000000 * 1); //delays for 1 second

        
    }
}

static bool I2C_writeTestByte(){

    uint32_t timeout;

    // 1) Wait for previous STOP to finish
    timeout = I2C_TIMEOUT;
    while (I2C_getStopConditionStatus(I2C_BASE) && --timeout); //make sure STOP condition has been set and nothing on line 
    if (timeout == 0U) return false;

    // 2) Wait for bus to be free
    timeout = I2C_TIMEOUT;
    while (I2C_isBusBusy(I2C_BASE) && --timeout); //Returns true of I2Cbus is busy, false if not. Repeats until it hits false
    if (timeout == 0U) return false;

    // 3) Set target and data count (1 byte)
    I2C_setTargetAddress(I2C_BASE, I2C_ADDR_TEST); //set target address
    I2C_setDataCount(I2C_BASE, 1); //set data transmit count

    // Controller‑transmit
    I2C_setConfig(I2C_BASE, I2C_CONTROLLER_SEND_MODE); //set configuration

    // 4) Load one dummy byte
    I2C_putData(I2C_BASE, 0xAA); //plaes a byte into the I2C transmit register

    // 5) START + STOP
    I2C_sendStartCondition(I2C_BASE); //send the start condition
    I2C_sendStopCondition(I2C_BASE); //end transmission with stop

    // 6) Wait for STOP complete
    timeout = I2C_TIMEOUT;
    while (!I2C_getStopConditionStatus(I2C_BASE) && --timeout); //again wait for the hardare to finish out the stop condition
    if (timeout == 0U) return false;

    return true;

}

//
// End of File
//
