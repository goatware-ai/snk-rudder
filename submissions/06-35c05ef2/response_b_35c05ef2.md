# Response B (schema slot: response_text_y)

<!-- model: 8285abc8545d4a5da065f1bb8f87cf38 -->

**Don't just throw it into a generic image classifier.** While a standard classification model might *eventually* work, captchas are designed to defeat general models. 

Instead, **do something more specific: train the AI to recognize the underlying feature (Direction), not the objects themselves.**

Here is the best way to approach this:

### The "Direction Extraction" Strategy (Recommended)
Don't train the AI to identify "Dog looking left" vs "Arrow pointing right". Instead, train it to classify a single image based purely on its **orientation** (e.g., `Left`, `Right`, `Up`, `Down`).

1. **Labeling:** Label every single cropped image (both animals and arrows) with only its direction. Don't label it as "Cat" or "Arrow", just label it `Left`, `Right`, `Up`, or `Down`.
2. **Architecture:** Use a lightweight CNN. A heavy ResNet50 is overkill and slow. Use **MobileNetV3**, **EfficientNet-Lite**, or even a custom few-layer CNN. 
3. **Training:** Train it as a 4-class (or 4-output regression if using degrees 0-360) image classification problem.
4. **The Solver Logic (Python):** Once trained, your script does this:
   * Pass **all** cropped images through the model to get their predicted direction.
   * Isolate the image identified as the "Arrow" (you can often identify it by aspect ratio or just test all images to see which one acts as an arrow).
   * Find the animal image whose predicted direction matches the arrow's direction.
   * *If multiple animals match, look for subtle hints (e.g., the animal is usually centered, or has a higher confidence score).*

**Why this is better:** 
If the captcha creator changes the animals from cats to cars tomorrow, a generic "Cat/Arrow" classifier will break. A "Direction" classifier will still work because cars and cats both have orientations.

### What the architecture looks like:
* **Input:** 64x64 or 128x128 RGB image.
* **Base:** 3 Conv2D blocks (Conv -> ReLU -> MaxPool), OR a pre-trained MobileNetV3 (frozen, then fine-tuned).
* **Head:** Flatten/Dropout -> Dense(128) -> Dense(4) + Softmax.
* **Output:** `[0.05, 0.85, 0.05, 0.05]` (85% confident it's pointing Right).

### Critical Captcha-Specific Tips:
If you don't do this, the captcha provider will block you within 24 hours:

* **Do NOT rotate images in data augmentation.** If you rotate an image of an animal looking right, it now looks down. If your augmentation flips it horizontally, "Right" becomes "Left". *Only use augmentation that doesn't change direction: slight blurs, brightness/contrast jittering, and tiny (1-2 pixel) translations.*
* **Handle Adversarial Noise:** Captchas often have dotted lines, grids, or color-shifting grids laid over the image. Augment your training data by programmatically adding random dotted lines or gaussian noise over your training images.
* **Use ONNX for Inference:** Python + PyTorch is too slow for real-time captcha solving. Train in PyTorch/TensorFlow, export to **ONNX**, and run inference in Python using `onnxruntime`. This will drop your solving time from ~2 seconds to ~0.05 seconds.
* **Temperature Scaling:** Captcha APIs usually return bounding boxes or ask you to click specific coordinates. Make sure your model outputs a calibrated confidence score so you know when it is "unsure" (in which case you should refresh the captcha rather than submitting a wrong guess).
