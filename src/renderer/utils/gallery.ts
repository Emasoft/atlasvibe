/*
 * Copyright (c) 2024 Emasoft
 *
 * This file is part of AtlasVibe, which is based on Flojoy Studio
 * Original Copyright (c) 2023-2024 Flojoy
 *
 * SPDX-License-Identifier: MIT
 * See the LICENSE file for details.
 */

import { GalleryData } from "@/renderer/types/gallery";

export const data: GalleryData = {
  Fundamentals: [
    {
      title: "Intro to Loops",
      description: "Generate a random number once",
      imagePath: "assets/appGallery/introToLoops.png",
      appPath: "sample_projects/loop",
      relevantNodes: [
        {
          name: "LOOP",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/control-flow/#loops",
        },
      ],
      cloudDemoEnabled: true,
    },
    {
      title: "Butterworth Filter",
      description: "Apply a butterworth filter to an input signal",
      imagePath: "assets/appGallery/introToSignals.png",
      appPath: "sample_projects/butterworth",
      relevantNodes: [],
      cloudDemoEnabled: true,
    },
    {
      title: "Intro to Images",
      description: "Apply a butterworth filter on a sample image",
      imagePath: "assets/appGallery/introToImages.png",
      appPath: "sample_projects/images",
      relevantNodes: [
        {
          name: "IMAGE",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/data/visualization/plotly/image",
        },
      ],
      cloudDemoEnabled: true,
    },
  ],
  Oscilloscopes: [
    {
      title: "Tektronix",
      description: "Decode I2C messages with a MSO2X oscilloscope",
      imagePath: "assets/appGallery/MS024DecodeI2C.png",
      appPath: "sample_projects/MSO24DecodeI2C",
      relevantNodes: [
        {
          name: "DECODE_I2C_MSO2X",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/hardware/oscilloscopes/tektronix/mso2x/decode-i2c-mso2x/",
        },
      ],
      cloudDemoEnabled: false,
    },
    {
      title: "Tektronix",
      description: "Extract the trace from a MDO3XXX oscilloscope",
      imagePath: "assets/appGallery/mdo3ExtractTrace.png",
      appPath: "sample_projects/mdo3ExtractTrace",
      relevantNodes: [
        {
          name: "EXTRACT_TRACE_MDO3XXX",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/hardware/oscilloscopes/tektronix/mdo3xxx/extract-trace-mdo3xxx/",
        },
      ],
      cloudDemoEnabled: false,
    },
    {
      title: "Rigol",
      description: "Extract a trace from a Rigol oscilloscope",
      imagePath: "assets/appGallery/rigolExtractTrace.png",
      appPath: "sample_projects/rigolExtractTrace",
      relevantNodes: [
        {
          name: "EXTRACT_TRACE_DS1074Z",
          docs: "https://github.com/Emasoft/atlasvibe#instruments-database/oscilloscopes/rigol/rigol-ds1074z/",
        },
      ],
      cloudDemoEnabled: false,
    },
    {
      title: "LeCroy",
      description: "Extract a trace from a Teledyne LeCryo T3DSO oscilloscope",
      imagePath: "assets/appGallery/LeCroyT3DSO.png",
      appPath: "sample_projects/leCroyExtractTrace",
      relevantNodes: [
        {
          name: "CONNECT_T3DSO1XXX",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/hardware/oscilloscopes/teledyne-lecroy/t3dso1xxx/connect-t3dso1xxx/",
        },
      ],
      cloudDemoEnabled: false,
    },
    {
      title: "PICO",
      description: "Extract the trace from a P2000 PicoScope",
      imagePath: "assets/appGallery/picoExtractTrace.png",
      appPath: "sample_projects/picoExtractTrace",
      relevantNodes: [
        {
          name: "EXTRACT_TRACE_2000",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/hardware/oscilloscopes/pico/pico2000/extract-trace-2000/",
        },
      ],
      cloudDemoEnabled: false,
    },
  ],
  Function_Generators: [
    {
      title: "Bode Plot",
      description:
        "Create a Bode plot with a function generator and an oscilloscope",
      imagePath:
        "https://res.cloudinary.com/dhopxs1y3/image/upload/v1692118735/Instruments/Function%20Generators/AFG3000/AFG3000.png",
      appPath: "sample_projects/bodePlot",
      relevantNodes: [
        {
          name: "INPUT_PARAM_AFG31000",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/hardware/function-generators/tektronix/afg31000/input-param-afg31000/",
        },
      ],
      cloudDemoEnabled: false,
    },
  ],
  DAQ: [
    {
      title: "LabJack",
      description: "Record and log temperatures",
      imagePath: "assets/appGallery/labjack.png",
      appPath: "sample_projects/labjack",
      relevantNodes: [
        {
          name: "READ_ANALOG_LABJACKU3",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/hardware/daq-boards/labjack/u3/read-a0-pins/",
        },
      ],
      cloudDemoEnabled: false,
    },
    {
      title: "Arduino",
      description: "Read from any analog sensor",
      imagePath: "assets/appGallery/arduino.png",
      appPath: "sample_projects/arduino",
      relevantNodes: [],
      cloudDemoEnabled: false,
    },
    {
      title: "Read Analog value from NI CompactDAQ",
      description: "Record current value from a NI CompactDAQ",
      imagePath: "assets/appGallery/NIcDAQ.png",
      appPath: "sample_projects/cDAQReadAnalog",
      relevantNodes: [
        {
          name: "CONNECT_COMPACTDAQ",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/hardware/daq-boards/national-instruments/compact-daq/create-task/",
        },
        {
          name: "ANALOG_INPUT",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/hardware/daq-boards/national-instruments/compact-daq/attach-analog-input-current/",
        },
      ],
      cloudDemoEnabled: false,
    },
  ],
  Multimeters_Sourcemeters: [
    {
      title: "IV Sweep",
      description: "Perform an IV sweep",
      imagePath: "assets/appGallery/2450.png",
      appPath: "sample_projects/IVSweep",
      relevantNodes: [
        {
          name: "IV_SWEEP_2450",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/hardware/sourcemeters/keithley/2450/iv-sweep-2450/",
        },
      ],
      cloudDemoEnabled: false,
    },
    {
      title: "Measure Voltage",
      description: "Read DC voltage using a digital multimeter",
      imagePath: "assets/appGallery/dmm.png",
      appPath: "sample_projects/dmmRead",
      relevantNodes: [
        {
          name: "READ_MEASUREMENT_DMM7510",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/hardware/multimeters/keithley/dmm7510/read-measurement-dmm7510/",
        },
      ],
      cloudDemoEnabled: false,
    },
  ],
  Protocols: [
    {
      title: "Read CAN Bus",
      description:
        "Connect to a PEAK-USB device to capture CAN Bus messages and log them into a .mf4 file for analysis and storage",
      imagePath: "assets/appGallery/peak-usb.png",
      appPath: "sample_projects/canReadAndLog",
      relevantNodes: [
        {
          name: "CONNECT_PCAN",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/hardware/protocols/can/bus/peak-connect/",
        },
        {
          name: "RECEIVE_MESSAGE",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/hardware/protocols/can/bus/receive-can-message/",
        },
      ],
      cloudDemoEnabled: false,
    },
    {
      title: "Send CAN Bus Messages",
      description:
        "Connect to a CANable USB-CAN device and transmit frames onto a CAN Bus network.",
      imagePath: "assets/appGallery/canable-usb.png",
      appPath: "sample_projects/canSend",
      relevantNodes: [
        {
          name: "CONNECT_SLCAN",
          docs: "https://https://github.com/Emasoft/atlasvibe#blocks/hardware/protocols/can/bus/send-can-message/",
        },
        {
          name: "SEND_MESSAGE",
          docs: "https://https://github.com/Emasoft/atlasvibe#blocks/hardware/protocols/can/bus/send-can-message/",
        },
      ],
      cloudDemoEnabled: false,
    },
  ],
  Signal_Analyzers: [],
  IO: [
    {
      title: "USB Camera",
      description: "Capture real-time images",
      imagePath: "assets/appGallery/usbCamera.png",
      appPath: "sample_projects/webcam",
      relevantNodes: [
        {
          name: "OPEN_WEBCAM",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/hardware/imaging/open-webcam/#_top",
        },
      ],
      cloudDemoEnabled: true,
    },
    {
      title: "Stepper Motor",
      description: "Precisely position anything",
      imagePath: "assets/appGallery/stepperMotor.png",
      appPath: "sample_projects/stepper",
      relevantNodes: [
        {
          name: "CONTROL_TIC_DRIVER",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/hardware/motors/stepper/polulu/tic/",
        },
      ],
      cloudDemoEnabled: false,
    },
  ],
  DSP: [
    {
      title: "PID Controller",
      description: "Solve this non-linear dynamic system",
      imagePath: "assets/appGallery/PID.png",
      appPath: "sample_projects/pid",
      relevantNodes: [],
      cloudDemoEnabled: true,
    },
    {
      title: "FIR Filter",
      description: "Apply an FIR filter to an input signal",
      imagePath: "assets/appGallery/FIR.png",
      appPath: "sample_projects/fir",
      relevantNodes: [
        {
          name: "FIR",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/dsp/fir/",
        },
      ],
      cloudDemoEnabled: true,
    },
    {
      title: "FFT",
      description: "Apply a real-time FFT to an input signal",
      imagePath: "assets/appGallery/FFT.png",
      appPath: "sample_projects/fft",
      relevantNodes: [
        {
          name: "FFT",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/dsp/fft/",
        },
      ],
      cloudDemoEnabled: true,
    },
    {
      title: "IFFT",
      description: "Transform a signal with the IFFT algorithm",
      imagePath: "assets/appGallery/IFFT.png",
      appPath: "sample_projects/ifft",
      relevantNodes: [
        {
          name: "IFFT",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/dsp/ifft/",
        },
      ],
      cloudDemoEnabled: true,
    },
  ],
  AI: [
    {
      title: "Image Captioning",
      description: "Caption any image with this PyTorch ML model",
      imagePath: "assets/appGallery/imageCaptioning.png",
      appPath: "sample_projects/imageCaptioning",
      relevantNodes: [
        {
          name: "NLP_CONNECT_VIT_GPT2",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/ai-ml/image-captioning/nlp-connect-vit-gpt2",
        },
      ],
      cloudDemoEnabled: true,
    },
    {
      title: "Image Classification",
      description: "Classify any image using Hugging Face Transformers",
      imagePath: "assets/appGallery/imageClassification.png",
      appPath: "sample_projects/imageClassification",
      relevantNodes: [
        {
          name: "HUGGING_FACE_PIPELINE",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/ai-ml/image-classification/hugging-face-pipeline/",
        },
      ],
      cloudDemoEnabled: true,
    },
    {
      title: "Time Series Forecasting",
      description: "Predict future events with the Prophet node",
      imagePath: "assets/appGallery/timeSeries.png",
      appPath: "sample_projects/prophet",
      relevantNodes: [
        {
          name: "PROPHET_PREDICT",
          docs: "https://github.com/Emasoft/atlasvibe#blocks/ai-ml/predict-time-series/prophet-predict/",
        },
      ],
      cloudDemoEnabled: true,
    },
  ],
};

export const getGalleryData = () => {
  return GalleryData.parse(data);
};
