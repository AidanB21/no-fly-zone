/*
 * Copyright (c) 2020 Texas Instruments Incorporated - http://www.ti.com
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * *  Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 * *  Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * *  Neither the name of Texas Instruments Incorporated nor the names of
 *    its contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
 * THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
 * CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 * EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 * PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
 * OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
 * OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
 * EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 */

#ifndef BOARD_H
#define BOARD_H

//*****************************************************************************
//
// If building with a C++ compiler, make all of the definitions in this header
// have a C binding.
//
//*****************************************************************************
#ifdef __cplusplus
extern "C"
{
#endif

//
// Included Files
//

#include "driverlib.h"
#include "device.h"

//*****************************************************************************
//
// PinMux Configurations
//
//*****************************************************************************

//*****************************************************************************
//
// ADC Configurations
//
//*****************************************************************************
#define myADCA_BASE ADCA_BASE
#define myADCA_RESULT_BASE ADCARESULT_BASE
#define J3P30 ADC_SOC_NUMBER0
#define J3P30_FORCE ADC_FORCE_SOC0
#define J3P30_ADC_BASE ADCA_BASE
#define J3P30_RESULT_BASE ADCARESULT_BASE
#define J3P30_SAMPLE_WINDOW 250
#define J3P30_TRIGGER_SOURCE ADC_TRIGGER_SW_ONLY
#define J3P30_CHANNEL ADC_CH_ADCIN0
#define J3P29 ADC_SOC_NUMBER1
#define J3P29_FORCE ADC_FORCE_SOC1
#define J3P29_ADC_BASE ADCA_BASE
#define J3P29_RESULT_BASE ADCARESULT_BASE
#define J3P29_SAMPLE_WINDOW 250
#define J3P29_TRIGGER_SOURCE ADC_TRIGGER_SW_ONLY
#define J3P29_CHANNEL ADC_CH_ADCIN2
#define J3P26 ADC_SOC_NUMBER2
#define J3P26_FORCE ADC_FORCE_SOC2
#define J3P26_ADC_BASE ADCA_BASE
#define J3P26_RESULT_BASE ADCARESULT_BASE
#define J3P26_SAMPLE_WINDOW 250
#define J3P26_TRIGGER_SOURCE ADC_TRIGGER_SW_ONLY
#define J3P26_CHANNEL ADC_CH_ADCIN3
void myADCA_init();

#define myADCB_BASE ADCB_BASE
#define myADCB_RESULT_BASE ADCBRESULT_BASE
#define J3P28 ADC_SOC_NUMBER0
#define J3P28_FORCE ADC_FORCE_SOC0
#define J3P28_ADC_BASE ADCB_BASE
#define J3P28_RESULT_BASE ADCBRESULT_BASE
#define J3P28_SAMPLE_WINDOW 250
#define J3P28_TRIGGER_SOURCE ADC_TRIGGER_SW_ONLY
#define J3P28_CHANNEL ADC_CH_ADCIN2
#define J3P25 ADC_SOC_NUMBER1
#define J3P25_FORCE ADC_FORCE_SOC1
#define J3P25_ADC_BASE ADCB_BASE
#define J3P25_RESULT_BASE ADCBRESULT_BASE
#define J3P25_SAMPLE_WINDOW 250
#define J3P25_TRIGGER_SOURCE ADC_TRIGGER_SW_ONLY
#define J3P25_CHANNEL ADC_CH_ADCIN3
void myADCB_init();


//*****************************************************************************
//
// Board Configurations
//
//*****************************************************************************
void	Board_init();
void	ADC_init();
void	PinMux_init();

//*****************************************************************************
//
// Mark the end of the C bindings section for C++ compilers.
//
//*****************************************************************************
#ifdef __cplusplus
}
#endif

#endif  // end of BOARD_H definition
