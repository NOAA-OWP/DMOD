# PartitionRequest

**Title:** PartitionRequest

|                           |                                                                           |
| ------------------------- | ------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                  |
| **Required**              | No                                                                        |
| **Additional properties** | [[Any type: allowed]](# "Additional Properties of any type are allowed.") |

**Description:** Request for partitioning of the catchments in a hydrofabric, typically for distributed processing.

<details>
<summary><strong> <a name="partition_count"></a>1. [Required] Property PartitionRequest > partition_count</strong>  

</summary>
<blockquote>

**Title:** Partition Count

|              |           |
| ------------ | --------- |
| **Type**     | `integer` |
| **Required** | Yes       |

</blockquote>
</details>

<details>
<summary><strong> <a name="uuid"></a>2. [Optional] Property PartitionRequest > uuid</strong>  

</summary>
<blockquote>

**Title:** Uuid

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

**Description:** Get (as a string) the UUID for this instance.

</blockquote>
</details>

<details>
<summary><strong> <a name="hydrofabric_uid"></a>3. [Required] Property PartitionRequest > hydrofabric_uid</strong>  

</summary>
<blockquote>

**Title:** Hydrofabric Uid

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

**Description:** The unique identifier for the hydrofabric that is to be partitioned.

</blockquote>
</details>

<details>
<summary><strong> <a name="hydrofabric_data_id"></a>4. [Optional] Property PartitionRequest > hydrofabric_data_id</strong>  

</summary>
<blockquote>

**Title:** Hydrofabric Data Id

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

**Description:** When known, the 'data_id' for the dataset containing the associated hydrofabric.

</blockquote>
</details>

<details>
<summary><strong> <a name="hydrofabric_description"></a>5. [Optional] Property PartitionRequest > hydrofabric_description</strong>  

</summary>
<blockquote>

**Title:** Hydrofabric Description

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |

**Description:** The optional description or name of the hydrofabric that is to be partitioned.

</blockquote>
</details>

----------------------------------------------------------------------------------------------------------------------------
