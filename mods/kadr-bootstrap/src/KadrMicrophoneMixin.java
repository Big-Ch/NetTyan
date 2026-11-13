package kadr.voice.mixin;

import de.maxhenkel.voicechat.voice.client.microphone.Microphone;
import de.maxhenkel.voicechat.voice.client.microphone.MicrophoneManager;
import kadr.voice.KadrSyntheticMicrophone;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = MicrophoneManager.class, remap = false)
public abstract class KadrMicrophoneMixin {
    @Inject(method = "createMicrophone", at = @At("HEAD"), cancellable = true, remap = false)
    private static void useSyntheticInput(CallbackInfoReturnable<Microphone> result) {
        if (System.getProperty("kadr.voice.pcm") != null) {
            KadrSyntheticMicrophone microphone = new KadrSyntheticMicrophone();
            microphone.open();
            result.setReturnValue(microphone);
        }
    }
}
