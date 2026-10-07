import argparse
import copy
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from starter.datasets import dataset_type, load_frame
from starter.projection import perturb_extrinsic, project_velo_to_image, overlay_points, draw_box2d

def points_in_bbox(uv: np.ndarray, bbox: tuple[float, float, float, float]) -> int:
    x1, y1, x2, y2 = bbox
    u, v = uv[:, 0], uv[:, 1]
    mask = (u >= x1) & (u <= x2) & (v >= y1) & (v <= y2)
    return int(mask.sum())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data/kitti_mini")
    ap.add_argument("--frame", default="000011")
    ap.add_argument("--out-csv", default="results/yaw_perturb_sweep.csv")
    args = ap.parse_args()

    fr = load_frame(args.data_root, args.frame)
    original_points = fr["points"]
    image_shape = fr["image"].shape
    bboxes = [obj.bbox for obj in fr["labels"]]
    
    results = []
    
    # Sweep yaw from 0 to 3 degrees
    for yaw_deg in [0.0, 1.0, 2.0, 3.0]:
        calib = perturb_extrinsic(fr["calib"], yaw_deg=yaw_deg)
        uv, depth, mask = project_velo_to_image(original_points, calib, image_shape)
        
        total_valid = int(mask.sum())
        total_points = len(mask)
        pct_in_fov = total_valid / total_points * 100
        
        # Count points in all bboxes
        points_in_boxes = 0
        for bbox in bboxes:
            points_in_boxes += points_in_bbox(uv, bbox)
            
        pct_in_boxes = (points_in_boxes / total_valid * 100) if total_valid > 0 else 0
        
        results.append({
            "yaw_deg": yaw_deg,
            "points_in_fov": total_valid,
            "pct_in_fov": pct_in_fov,
            "points_in_boxes": points_in_boxes,
            "pct_in_boxes": pct_in_boxes
        })
        
        # Save image for this perturb level
        vis = overlay_points(fr["image"], uv, depth)
        for obj in fr["labels"]:
            vis = draw_box2d(vis, obj.bbox, label=obj.type)
        
        out_img_path = Path(f"results/figures/fail_01_yaw_{yaw_deg}deg.png") if yaw_deg > 0 else Path(f"results/figures/demo_yaw_{yaw_deg}deg.png")
        out_img_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_img_path), vis)
        
    df = pd.DataFrame(results)
    df.to_csv(args.out_csv, index=False)
    print(df)
    
    # Create a plot
    import matplotlib.pyplot as plt
    plt.figure(figsize=(8, 5))
    plt.plot(df["yaw_deg"], df["pct_in_boxes"], marker='o', linewidth=2, color='b')
    plt.title("Tỉ lệ điểm LiDAR rơi vào 2D box theo độ lệch Yaw")
    plt.xlabel("Mức lệch Yaw (độ)")
    plt.ylabel("% Điểm trong 2D box")
    plt.grid(True)
    plt.savefig("results/figures/yaw_perturb_plot.png")
    plt.close()
    
if __name__ == "__main__":
    main()
