use criterion::{black_box, criterion_group, criterion_main, Criterion};
use std::path::Path;

fn bench_is_test_file(c: &mut Criterion) {
    let samples = [
        "test_foo.py",
        "foo_test.py",
        "regular.py",
        "test_",
        "_test.py",
        "very_long_test_file_name_with_many_characters.py",
        "setup.py",
        "conftest.py",
        "test_bar.txt",
        "src/tests/test_mod.py",
    ];

    c.bench_function("is_test_file_variants", |b| {
        b.iter(|| {
            for s in &samples {
                let _ = black_box(s.starts_with("test_") || s.ends_with("_test.py"));
            }
        });
    });
}

fn bench_test_item_creation(c: &mut Criterion) {
    let path = "/home/user/project/src/tests/test_module.py".to_string();
    let name = "test_function_that_does_something_important".to_string();

    c.bench_function("test_item_creation", |b| {
        b.iter(|| {
            let _ = black_box(oxytest_core::types::TestItem::new_no_args(
                black_box(path.clone()),
                black_box(name.clone()),
                black_box(42u32),
            ));
        });
    });
}

fn bench_test_item_clone(c: &mut Criterion) {
    let item = oxytest_core::types::TestItem::new_no_args(
        "/path/to/test_file.py".into(),
        "test_some_function".into(),
        15,
    );

    c.bench_function("test_item_clone", |b| {
        b.iter(|| {
            let _ = black_box(black_box(&item).clone());
        });
    });
}

fn bench_test_result_creation(c: &mut Criterion) {
    let test = oxytest_core::types::TestItem::new_no_args(
        "/path/t.py".into(),
        "test_ok".into(),
        1,
    );

    c.bench_function("test_result_passed", |b| {
        b.iter(|| {
            let _ = black_box(oxytest_core::types::TestResult::passed(
                black_box(test.clone()),
                black_box("output".into()),
                black_box("error_output".into()),
                black_box(42u64),
            ));
        });
    });

    c.bench_function("test_result_failed", |b| {
        b.iter(|| {
            let _ = black_box(oxytest_core::types::TestResult::failed(
                black_box(test.clone()),
                black_box(String::new()),
                black_box(String::new()),
                black_box(10u64),
                black_box("AssertionError".into()),
                black_box(Some("traceback line 1\ntraceback line 2".into())),
            ));
        });
    });
}

criterion_group!(
    benches,
    bench_is_test_file,
    bench_test_item_creation,
    bench_test_item_clone,
    bench_test_result_creation,
);
criterion_main!(benches);
