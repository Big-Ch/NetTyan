package kadr.voice;

import de.maxhenkel.voicechat.voice.client.microphone.Microphone;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;

/** A 48 kHz synthetic source for the isolated bot profile. */
public final class KadrSyntheticMicrophone implements Microphone {
    private static final int SAMPLES = 960;
    private final Path clip = Path.of(System.getProperty("kadr.voice.pcm"));
    private boolean open;
    private boolean started;
    private long nextFrame;
    private InputStream audio;

    public void open() { open = true; }
    public void start() { started = true; nextFrame = System.nanoTime(); }
    public boolean isOpen() { return open; }
    public boolean isStarted() { return started; }
    public int available() { return started && System.nanoTime() >= nextFrame ? SAMPLES : 0; }

    public short[] read() {
        nextFrame = System.nanoTime() + 20_000_000L;
        short[] samples = new short[SAMPLES];
        try {
            if (!Files.isRegularFile(clip)) {
                closeAudio();
                return samples;
            }
            if (audio == null) audio = Files.newInputStream(clip);
            byte[] bytes = audio.readNBytes(SAMPLES * 2);
            ByteBuffer pcm = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN);
            for (int i = 0; pcm.remaining() >= 2; i++) samples[i] = pcm.getShort();
            if (bytes.length < SAMPLES * 2) {
                closeAudio();
                Files.deleteIfExists(clip);
            }
        } catch (IOException error) {
            closeAudio();
        }
        return samples;
    }

    private void closeAudio() {
        if (audio == null) return;
        try { audio.close(); } catch (IOException ignored) {}
        audio = null;
    }

    public void stop() { started = false; closeAudio(); }
    public void close() { stop(); open = false; }
}
