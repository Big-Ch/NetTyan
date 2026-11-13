import java.util.concurrent.Executor;
import java.util.concurrent.atomic.AtomicBoolean;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.loader.api.FabricLoader;
import net.fabricmc.loader.api.MappingResolver;

/** Initialize the existing UnionClef when vanilla Quick Play skips TitleScreen. */
public final class KadrBootstrap implements ModInitializer {
    public void onInitialize() {
        Thread worker = new Thread(() -> {
            AtomicBoolean done = new AtomicBoolean(false);
            for (int tries = 0; tries < 180 && !done.get(); tries++) {
                try {
                    MappingResolver mappings = FabricLoader.getInstance().getMappingResolver();
                    Class<?> type = Class.forName(mappings.mapClassName("intermediary", "net.minecraft.class_310"));
                    String getter = mappings.mapMethodName("intermediary", "net.minecraft.class_310", "method_1551", "()Lnet/minecraft/class_310;");
                    Object client = type.getMethod(getter).invoke(null);
                    if (client != null) {
                        ((Executor) client).execute(() -> {
                            try {
                                String player = mappings.mapFieldName("intermediary", "net.minecraft.class_310", "field_1724", "Lnet/minecraft/class_746;");
                                if (type.getField(player).get(client) == null) return;
                                Class<?> alto = Class.forName("adris.altoclef.AltoClef");
                                Object mod = alto.getMethod("getInstance").invoke(null);
                                if (mod == null) return;
                                if (alto.getMethod("getSlotHandler").invoke(mod) == null) {
                                    alto.getMethod("onInitializeLoad").invoke(mod);
                                    System.out.println("[Kadr] UnionClef initialized for Quick Play");
                                }
                                done.set(true);
                            } catch (Throwable error) {
                                System.err.println("[Kadr] Quick Play initialization: " + error.getClass().getSimpleName());
                            }
                        });
                    }
                    Thread.sleep(500);
                } catch (Throwable error) {
                    try { Thread.sleep(500); } catch (InterruptedException stop) { return; }
                }
            }
        }, "Kadr-QuickPlay-init");
        worker.setDaemon(true);
        worker.start();
    }
}
