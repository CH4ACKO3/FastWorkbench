"""Contract regression for the production RecipeCache helper.

Run with Python 3 and a JDK on PATH. Compiles the real helper against
minimal API fixtures; not a substitute for a Forge/Polymorph integration test.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
fixtures = {
    "net/minecraft/world/item/ItemStack.java": """
package net.minecraft.world.item;
public class ItemStack { public static final ItemStack EMPTY = new ItemStack(); }
""",
    "net/minecraft/world/inventory/CraftingContainer.java": """
package net.minecraft.world.inventory;
public class CraftingContainer {}
""",
    "net/minecraft/world/item/crafting/RecipeType.java": """
package net.minecraft.world.item.crafting;
public class RecipeType { public static final RecipeType CRAFTING = new RecipeType(); }
""",
    "net/minecraft/world/item/crafting/Recipe.java": """
package net.minecraft.world.item.crafting;
import net.minecraft.world.level.Level;
public interface Recipe<C> {
    String getId();
    RecipeType getType();
    boolean matches(C input, Level level);
}
""",
    "net/minecraft/world/item/crafting/RecipeManager.java": """
package net.minecraft.world.item.crafting;
import java.util.*;
import net.minecraft.world.inventory.CraftingContainer;
import net.minecraft.world.level.Level;
public class RecipeManager {
    public Map<RecipeType, Map<String, Recipe<?>>> recipes = new HashMap<>();
    // Deliberately independent, as in script-driven recipe updates.
    public Map<String, Recipe<?>> byName = new HashMap<>();
    @SuppressWarnings("unchecked")
    public Optional<Recipe<CraftingContainer>> getRecipeFor(RecipeType type, CraftingContainer input, Level level) {
        return recipes.getOrDefault(type, Map.of()).values().stream()
            .map(r -> (Recipe<CraftingContainer>) r).filter(r -> r.matches(input, level)).findFirst();
    }
}
""",
    "net/minecraft/world/level/Level.java": """
package net.minecraft.world.level;
import net.minecraft.world.item.crafting.RecipeManager;
public class Level {
    public boolean isClientSide;
    public RecipeManager manager = new RecipeManager();
    public RecipeManager getRecipeManager() { return manager; }
}
""",
    "net/minecraft/world/inventory/ResultContainer.java": """
package net.minecraft.world.inventory;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.Recipe;
public class ResultContainer {
    public Recipe<?> recipe;
    public ItemStack item = new ItemStack();
    public Recipe<?> getRecipeUsed() { return recipe; }
    public void setRecipeUsed(Recipe<?> value) { recipe = value; }
    public void setItem(int slot, ItemStack value) { item = value; }
}
""",
    "dev/shadowsoffire/fastbench/util/RecipeCacheTest.java": """
package dev.shadowsoffire.fastbench.util;
import java.util.*;
import net.minecraft.world.inventory.*;
import net.minecraft.world.item.*;
import net.minecraft.world.item.crafting.*;
import net.minecraft.world.level.*;
public class RecipeCacheTest {
    record TestRecipe(String getId, boolean valid) implements Recipe<CraftingContainer> {
        public RecipeType getType() { return RecipeType.CRAFTING; }
        public boolean matches(CraftingContainer input, Level level) { return valid; }
    }
    static int count;
    static void check(boolean value) { count++; if (!value) throw new AssertionError(count); }
    public static void main(String[] args) {
        Level level = new Level();
        var recipes = new HashMap<String, Recipe<?>>();
        level.manager.recipes.put(RecipeType.CRAFTING, recipes);
        var old = new TestRecipe("test:recipe", true);
        var replacement = new TestRecipe("test:recipe", true);
        var input = new CraftingContainer();
        var result = new ResultContainer();
        result.setRecipeUsed(old);
        recipes.put(old.getId(), old);
        check(RecipeCache.current(result, level) == old);
        check(result.item != ItemStack.EMPTY);
        level.manager.byName.put(old.getId(), old);
        recipes.put(old.getId(), replacement);
        check(RecipeCache.current(result, level) == null);
        check(result.recipe == null && result.item == ItemStack.EMPTY);
        // Keep a valid same-ID choice from an integration, but use its new instance.
        check(RecipeCache.resolve(old, input, level) == replacement);
        recipes.clear();
        result.setRecipeUsed(old);
        result.item = new ItemStack();
        check(RecipeCache.current(result, level) == null);
        check(result.item == ItemStack.EMPTY);
        check(RecipeCache.resolve(old, input, level) == null);
        var alternative = new TestRecipe("test:alternative", true);
        recipes.put(alternative.getId(), alternative);
        check(RecipeCache.resolve(old, input, level) == alternative);
        recipes.put(old.getId(), new TestRecipe(old.getId(), false));
        check(RecipeCache.resolve(old, input, level) == alternative);
        check(RecipeCache.resolve(null, input, level) == alternative);
        level.isClientSide = true;
        result.setRecipeUsed(old);
        check(RecipeCache.current(result, level) == old);
        System.out.println(count+" recipe cache contract checks passed");
    }
}
""",
}
helper = "dev/shadowsoffire/fastbench/util/RecipeCache.java"
fixtures[helper] = (root / "src/main/java" / helper).read_text()
with tempfile.TemporaryDirectory() as directory:
    files = []
    for name, source in fixtures.items():
        path = Path(directory) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        files.append(str(path))
    subprocess.run(["javac", "-d", directory, *files], check=True)
    subprocess.run(["java", "-cp", directory,
                    "dev.shadowsoffire.fastbench.util.RecipeCacheTest"], check=True)
